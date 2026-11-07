// Excerpt from xLightsSequencer/xLights@a57c5ace577ca84421273d2f859a1a0c3f728297
// src-core/render/ValueCurve.cpp lines 1555-1607 (converting 0-100 normalized curves to real values on load)
// GPL-3.0. Kept for verification only, never copied into pewpew (architecture §9). Source entry [S1359].
        // if we are asked to hold min max then we are just going to use the ones we deserialised and assume parms are all ok
        // this is generally only done when loading an xvc file ... particularly an old one
        if (!holdminmax)
        {
            // This converts curves from the 0-100 to the real scale
            if (_active && !_realValues)
            {
                if (_min == 0 && _max == 100 && _divisor == 1)
                {
                    // no rescaling needed
                    _realValues = true;
                }
                else if (oldmin != MINVOIDF)
                {
                    if (_min != 0 || _max != 100)
                    {
                        // use the scale in the file if it wasnt 0-100
                        FixChangedScale(_min, _max, _divisor);
                    }
                    else
                    {
                        if (oldmin != 0 || oldmax != 100 || _divisor != 1)
                        {
                            // otherwise use the scale of this VC ... this is not great ... if the VC range has been expanded then
                            // it isnt going to convert correctly

                            // this is actually checking for something 2018.23 or newer
                            // this should be updated every release by 1 until we decide to change a slider range for the first time
                            // at that point we are going to need to force people to go back to a version after 2017.24 but before the
                            // first version with the change
                            if (!::IsVersionOlder("2018.46", xlights_version_string))
                            {
                                static std::string warnedfile = "";

                                std::string seqName = __sequenceElements ? __sequenceElements->GetRenderContext()->GetShowDirectory() : "";
                                if (!seqName.empty() && warnedfile != seqName)
                                {
                                    warnedfile = seqName;
                                    DisplayWarning("Sequence contains value curves that cannot be converted automatically. Please open and save this sequence in v2018.23 before proceeding.");
                                }
                            }
                            FixChangedScale(oldmin, oldmax, _divisor);
                        }
                    }
                    _realValues = true;
                }
            }

            // This converts curves to the new scale when a parameters range has been expanded ... but only if it was already real values
            if (_active && _realValues && ((oldmin != MINVOIDF && oldmin != _min) || (oldmax != MAXVOIDF && oldmax != _max)))
            {
                ConvertChangedScale(oldmin, oldmax);
            }
