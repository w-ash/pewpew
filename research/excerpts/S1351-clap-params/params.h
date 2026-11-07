// Excerpt from free-audio/clap@a47f6badb49d948fd009998f28309cdab78979c9
// include/clap/ext/params.h lines 78-115 (range changes, plain-value storage, modulation as plain delta)
// MIT License, Copyright (c) 2021 Alexandre BIQUE. Source entry [S1351].
/// CLAP allows the plugin to change the parameter range, yet the plugin developer
/// should be aware that doing so isn't without risk, especially if you made the
/// promise to never change the sound. If you want to be 100% certain that the
/// sound will not change with all host, then simply never change the range.
///
/// There are two approaches to automations, either you automate the plain value,
/// or you automate the knob position. The first option will be robust to a range
/// increase, while the second won't be.
///
/// If the host goes with the second approach (automating the knob position), it means
/// that the plugin is hosted in a relaxed environment regarding sound changes (they are
/// accepted, and not a concern as long as they are reasonable). Though, stepped parameters
/// should be stored as plain value in the document.
///
/// If the host goes with the first approach, there will still be situation where the
/// sound may inevitably change. For example, if the plugin increase the range, there
/// is an automation playing at the max value and on top of that an LFO is applied.
/// See the following curve:
///                                   .
///                                  . .
///          .....                  .   .
/// before: .     .     and after: .     .
///
/// Persisting parameter values:
///
/// Plugins are responsible for persisting their parameter's values between
/// sessions by implementing the state extension. Otherwise parameter value will
/// not be recalled when reloading a project. Hosts should _not_ try to save and
/// restore parameter values for plugins that don't implement the state
/// extension.
///
/// Advice for the host:
///
/// - store plain values in the document (automation)
/// - store modulation amount in plain value delta, not in percentage
/// - when you apply a CC mapping, remember the min/max plain values so you can adjust
/// - do not implement a parameter saving fall back for plugins that don't
///   implement the state extension

// lines 132-140 and 198-213 (stepped, periodic, enum flags; stable id)

enum {
   // Is this param stepped? (integer values only)
   // if so the double value is converted to integer using a cast (equivalent to trunc).
   CLAP_PARAM_IS_STEPPED = 1 << 0,

   // Useful for periodic parameters like a phase
   CLAP_PARAM_IS_PERIODIC = 1 << 1,

// ...
   //
   // A simple example would be a DC Offset, changing it will change the output signal and must be
   // processed.
   CLAP_PARAM_REQUIRES_PROCESS = 1 << 15,

   // This parameter represents an enumerated value.
   // If you set this flag, then you must set CLAP_PARAM_IS_STEPPED too.
   // All values from min to max must not have a blank value_to_text().
   CLAP_PARAM_IS_ENUM = 1 << 16,
};
typedef uint32_t clap_param_info_flags;

/* This describes a parameter */
typedef struct clap_param_info {
   // Stable parameter identifier, it must never change.
   clap_id id;
// ...
// lines 244-251 (name excludes the module; module is a display path)
   // The display name. eg: "Volume". This does not need to be unique. Do not include the module
   // text in this. The host should concatenate/format the module + name in the case where showing
   // the name alone would be too vague.
   char name[CLAP_NAME_SIZE];

   // The module path containing the param, eg: "Oscillators/Wavetable 1".
   // '/' will be used as a separator to show a tree-like structure.
   char module[CLAP_PATH_SIZE];
