/* InfiniteHybridInterpolator.cpp
*
*  MIT License
*
*  Copyright (c) 2020-2026 awawa-dev
*
*  Project homesite: https://github.com/awawa-dev/HyperHDR
*
*  Permission is hereby granted, free of charge, to any person obtaining a copy
*  of this software and associated documentation files (the "Software"), to deal
*  in the Software without restriction, including without limitation the rights
*  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
*  copies of the Software, and to permit persons to whom the Software is
*  furnished to do so, subject to the following conditions:
*
*  The above copyright notice and this permission notice shall be included in all
*  copies or substantial portions of the Software.

*  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
*  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
*  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
*  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
*  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
*  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
*  SOFTWARE.
 */

#ifndef PCH_ENABLED
	#include <QTimer>
	#include <QThread>	

	#include <cmath>
	#include <algorithm>
	#include <chrono>
	#include <iomanip>
	#include <iostream>
	#include <limits>
	#include <tuple>
	#include <vector>
	#include <cassert>
	#include <cstdint>
#endif

#include <infinite-color-engine/InfiniteHybridInterpolator.h>
#include <infinite-color-engine/ColorSpace.h>

using namespace linalg::aliases;

InfiniteHybridInterpolator::InfiniteHybridInterpolator() = default;

void InfiniteHybridInterpolator::setTransitionDuration(float durationMs)
{
	_initialDuration = std::max(1.0f, durationMs);
}

void InfiniteHybridInterpolator::setSpringiness(float stiffness, float damping)
{
	_stiffness = std::max(0.1f, stiffness);
	_damping = std::max(0.1f, damping);
}

void InfiniteHybridInterpolator::setMaxLuminanceChangePerFrame(float maxYChangePerFrame)
{
	_maxLuminanceChangePerStep = maxYChangePerFrame;
}

void InfiniteHybridInterpolator::resetToColors(std::vector<float3> colors, float startTimeMs)
{
	_currentColorsYUV.clear();
	setTargetColors(std::move(colors), startTimeMs);
}

void InfiniteHybridInterpolator::setTargetColors(std::vector<float3>&& new_rgb_to_yuv_targets, long long startTimeMs, bool debug) {
	if (new_rgb_to_yuv_targets.empty())
		return;

	const float delta = (!_isAnimationComplete) ? std::clamp(static_cast<float>(startTimeMs - _lastUpdate), 0.f, 100.0f) : 0.f;

	if (debug)
	{
		printf(" | Δ%.0f | time: %.0f | Y-limit: %.3f| stiffness: %.3f| damping: %.3f\n", delta, _initialDuration, _maxLuminanceChangePerStep, _stiffness, _damping);
	}

	startTimeMs -= delta;

	// convert incoming RGB to YUV
	_targetColorsRGB = new_rgb_to_yuv_targets;
	for (auto it_newTargetColorsYUV = new_rgb_to_yuv_targets.begin(); it_newTargetColorsYUV != new_rgb_to_yuv_targets.end(); ++it_newTargetColorsYUV)
	{
		*it_newTargetColorsYUV = ColorSpaceMath::rgb_to_bt709(*it_newTargetColorsYUV);
	}

	if (_currentColorsYUV.size() != new_rgb_to_yuv_targets.size() || _targetColorsYUV.size() != new_rgb_to_yuv_targets.size())
	{
		_lastUpdate = startTimeMs;
		_currentColorsYUV = new_rgb_to_yuv_targets;
		_targetColorsYUV = std::move(new_rgb_to_yuv_targets);
		_velocitiesYUV.assign(_currentColorsYUV.size(), float3{ 0,0,0 }); // NOWE
		_isAnimationComplete = true;
	}
	else
	{
		_targetColorsYUV = std::move(new_rgb_to_yuv_targets);
		_isAnimationComplete = false;
	}

	_startAnimationTimeMs = startTimeMs;
	_targetTime = startTimeMs + _initialDuration;
	_currentColorsRGB.reset();
}

void InfiniteHybridInterpolator::resetState() {
	_isAnimationComplete = true;
	_lastUpdate = 0;
	_targetColorsRGB.clear();
	_currentColorsRGB.reset();
	_currentColorsYUV.clear();
	_targetColorsYUV.clear();
	_velocitiesYUV.clear();
}

void InfiniteHybridInterpolator::updateCurrentColors(long long currentTimeMs, float minBrightness) {
	if (_isAnimationComplete)
	{
		_lastUpdate = currentTimeMs;
		return;
	}

	float dt = std::clamp(static_cast<float>(currentTimeMs - _lastUpdate), 0.001f, 100.0f);
	_lastUpdate = currentTimeMs;

	auto computeChannelVec = [&](float3& cur, const float3& diff, float3& vel) -> bool {
		constexpr float FINISH_COMPONENT_THRESHOLD = 0.0013732906f / 10.f;
		constexpr float VELOCITY_THRESHOLD = 0.0005f;

		if (linalg::maxelem(linalg::abs(diff)) < FINISH_COMPONENT_THRESHOLD && // color match
			linalg::maxelem(linalg::abs(vel)) < VELOCITY_THRESHOLD) // speed should be almost zero
		{
			cur += diff;
			vel = float3{ 0.f, 0.f, 0.f };
			return false;
		}
		else
		{
			float3 acc = _stiffness * diff - _damping * vel;

			// integracja (Euler semi-implicit)
			vel += acc * (dt * 0.001f);
			float3 step = vel * (dt * 0.001f);

			if (_maxLuminanceChangePerStep > 0.f && fabs(step[0]) > _maxLuminanceChangePerStep)
			{
				float scale = _maxLuminanceChangePerStep / fabs(step[0]);
				step *= scale;

				vel *= scale;
			}
			cur += step;

			const float3 minLimits{ minBrightness, -0.5f, -0.5f };
			constexpr float3 maxLimits{ 1.0f, 0.5f, 0.5f };
			for(int i = 0; i < 3; i++)
				if (cur[i] < minLimits[i] || cur[i] > maxLimits[i]){
					vel[i] = 0.0f;
					cur[i] = std::clamp(cur[i], minLimits[i], maxLimits[i]);
				}

			return true;
		}
	};

	_isAnimationComplete = true;

	for (auto cur = _currentColorsYUV.begin(), tgt = _targetColorsYUV.begin(), vel = _velocitiesYUV.begin();
		cur != _currentColorsYUV.end() && tgt != _targetColorsYUV.end() && vel != _velocitiesYUV.end();
		++cur, ++tgt, ++vel)
	{
		if (computeChannelVec(*cur, *tgt - *cur, *vel))
		{
			_isAnimationComplete = false;
		}
	}

	_currentColorsRGB.reset();
}

SharedOutputColors InfiniteHybridInterpolator::getCurrentColors(float minBrightness)
{
	if (!_currentColorsRGB.has_value())
	{
		if (_isAnimationComplete)
		{
			_currentColorsRGB = _targetColorsRGB;
		}
		else
		{
			std::vector<linalg::aliases::float3> tmp(_currentColorsYUV.size());
			std::transform(
				_currentColorsYUV.begin(),
				_currentColorsYUV.end(),
				tmp.begin(),
				[minBrightness](const auto& yuv) { return linalg::clamp(ColorSpaceMath::bt709_to_rgb(yuv), minBrightness, 1.0f); }
			);
			_currentColorsRGB = std::move(tmp);
		}
	}
	return std::make_shared<std::vector<linalg::vec<float, 3>>>(_currentColorsRGB.value());
}

// [excerpt note: test() harness (lines 210-323 at pinned sha) omitted]
