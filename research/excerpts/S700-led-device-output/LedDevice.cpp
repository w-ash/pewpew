// Excerpt from awawa-dev/HyperHDR@6d5fe8769c8e3d070003a25952d07424a2ae2584
// sources/led-drivers/LedDevice.cpp lines 537-546, 625-678, verbatim. MIT; Copyright (c) 2020-2026 awawa-dev.
// Source entry [S700]. See LICENSE-NOTE.md.
// lines 537-546
		if (!_isRefreshEnabled)
		{
			if (_newFrame2Send)
				_computeStats.droppedFrames++;
			_newFrame2Send = true;
			emit SignalManualUpdate();
		}
		else if (QThread::currentThread() == this->thread())
			rewriteLEDs();
	}
// lines 625-678
int LedDevice::write(SharedOutputColors nonlinearRgbColors)
{
	if (nonlinearRgbColors == nullptr || nonlinearRgbColors->empty())
		return 0;

	if (auto res = writeInfiniteColors(nonlinearRgbColors); !res.first)
	{
		// finity output using antiflickering filter
		if (_antiFlickeringFilter)
		{
			if (nonlinearRgbColors->size() == _lastFinityLedValues->size())
			{
				std::vector<ColorRgb> ledValues;
				ledValues.reserve(nonlinearRgbColors->size());

				for (size_t i = 0; i < nonlinearRgbColors->size(); ++i) {
					auto& oldV = (*_lastFinityLedValues)[i];
					const auto& newV = (*nonlinearRgbColors)[i];

					if (linalg::maxelem(linalg::abs(newV - oldV) * 255.0f) > 0.49f)
					{
						oldV = newV;
					}

					auto b = ColorSpaceMath::round_to_0_255<linalg::aliases::byte3>(oldV * 255.0f);
					ledValues.push_back({ b.x, b.y, b.z });
				}
				return writeFiniteColors(ledValues);
			}
			else
			{
				*_lastFinityLedValues = *nonlinearRgbColors;
			}
		}

		// default finity output
		std::vector<ColorRgb> ledValues;
		ledValues.reserve(nonlinearRgbColors->size());
		std::transform(nonlinearRgbColors->cbegin(), nonlinearRgbColors->cend(), std::back_inserter(ledValues),
			[](const auto& v) {
				auto b = ColorSpaceMath::round_to_0_255<linalg::aliases::byte3>(v * 255.0f);
				return ColorRgb{ b.x, b.y, b.z };
			});
		return writeFiniteColors(ledValues);
	}
	else if (_antiFlickeringFilter)
	{
		_antiFlickeringFilter = false;
		Warning(_log, "AntiFlickeringFilter was requested to be enabled, but the {:s} LED driver supports deep color and does not need it, so it is being disabled.", _activeDeviceType);
		return res.second;
	}
	else
		return res.second;
}
