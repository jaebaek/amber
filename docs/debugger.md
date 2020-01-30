# Debugger Testing

This document describes Amber's shader debugger testing framework, which allows developers to write tests for Vulkan drivers that expose shader debugging functionality via the [Debug Adapter Protocol](https://microsoft.github.io/debug-adapter-protocol/).

---
**Work In Progress**

Note that shader debugging is very much work-in-progress:

* Vulkan shader debugging currently does not have a formalized specification. A shader debugger implementation is being developed in [SwiftShader](https://swiftshader.googlesource.com/SwiftShader/), which one day may become a reference implementation for a formal specifiction.
* Currently SwiftShader is the only Vulkan driver to implement a [DAP based shader debugger](https://swiftshader.googlesource.com/SwiftShader/+/refs/heads/master/docs/VulkanShaderDebugging.md). This implementation is also work-in-progress, and may significantly change.
* Currently the debugger connection uses localhost sockets to connect Amber to the driver. The `VK_DEBUGGER_PORT` environment variable must be set to an unused localhost port number before attempting to run any Amber scripts that use the `DEBUG` command.
* [`OpenCL.DebugInfo.100`](https://www.khronos.org/registry/spir-v/specs/unified1/OpenCL.DebugInfo.100.mobile.html) is a SPIR-V extended instruction set that adds rich debug information to the shader program, allowing for high-level shader source debugging. `OpenCL.DebugInfo.100` is not currently generated by [DXC](https://github.com/microsoft/DirectXShaderCompiler) or [glslang](https://github.com/KhronosGroup/glslang), but initial work has started to try and add `OpenCL.DebugInfo.100` support to DXC.
* `OpenCL.DebugInfo.100` insstructions are not currently preserved by many of the [SPIR-V Tools](https://github.com/KhronosGroup/SPIRV-Tools) optimization passes, so these optimizations should not currently be used.
* `OpenCL.DebugInfo.100` may be incorrectly interpreted by the [SPIR-V Tools](https://github.com/KhronosGroup/SPIRV-Tools) validator, so Amber should currently be invoked with the `--disable-spirv-val` flag.

---

## Usage

### Building

The debugger testing functionality is disabled by default, and has to be enabled with the `AMBER_ENABLE_VK_DEBUGGING` CMake flag.

As SwiftShader is currently the only Vulkan driver that supports DAP-based shader debugging, you will also likely want to build SwiftShader as part of Amber, using the `AMBER_ENABLE_SWIFTSHADER` flag.

Both of these can be set by running CMake with:

```
cmake <path-to-amber-root> -DAMBER_ENABLE_SWIFTSHADER=1 -DAMBER_ENABLE_VK_DEBUGGING=1
```

### AmberScript

Debugger tests must be written in AmberScript.

The `DEBUG` command extends the [`RUN` command](amber_script.md#Run-a-pipeline) to execute a draw or compute shader.
`DEBUG` expects exactly the same arguments to follow as `RUN` ([see: 'Run a pipeline'](amber_script.md#Run-a-pipeline)). However, unlike `RUN`, `DEBUG` begins a block that must be terminated with an `END`.

Within this `RUN` block, you may declare any number of `THREAD` command blocks that list a sequence of debugger commands to perform on a single compute, vertex or fragment shader invocation:

* `THREAD GLOBAL_INVOCATION_ID` \<x\> \<y\> \<z\>

  Declares a sequence of debugger commands to run when the compute shader invocation with the given global invocation identifier is executed.

* `THREAD VERTEX_INDEX` \<index\>

  Declares a sequence of debugger commands to run when the shader invocation for the vertex with the given index is executed.

* `THREAD FRAGMENT_WINDOW_SPACE_POSITION` \<x\> \<y\>

  Defines a sequence of debugger commands to run when the shader invocation for the fragment with the given window space position is executed.

  TODO(bclayton): This has not yet been implemented.

Each of the `THREAD` commands begins a block that must be terminated with an `END`.

Within each `THREAD` command block, you may use any of the following commands to control execution of the shader, and to verify the debugger's behaviour:

* `STEP_IN`

  Single line step execution of the thread, stepping into any function calls.

* `STEP_OVER`

  Single line step execution of the thread, stepping over any function calls.

* `STEP_OUT`

  Run, without stopping to the end of the currently executing function. If the current function is not the top most of the call stack, then the debugger will pause at the next line after the function call.

* `EXPECT LOCATION` \<file name\> \<line number\> [\<line source\>]

  Verifies that the debugger is currently paused at the given line location.
  The [\<line source\>] is an additional, optional check that verifies the line of the file reported by the debuggeer is as expected.

* `EXPECT LOCAL` \<name\> `EQ` [\<value\>]

  Verifies that the local variable with the given name holds the expected value. \<name\> may contain `.` delimiters to index structure or array types.

Every shader invocation covered by a `THREAD` block must be executed.
It is a test failure if the debugger does not break at all the `THREAD` shader invocations declared in the `DEBUG` block.

#### Example:

Given the following HLSL vertex shader:

```hlsl
/*  1 */ // simple_vs.hlsl
/*  2 */ struct VS_OUTPUT {
/*  3 */   float4 pos : SV_POSITION;
/*  4 */   float4 color : COLOR;
/*  5 */ };
/*  6 */
/*  7 */ VS_OUTPUT main(float4 pos : POSITION,
/*  8 */                float4 color : COLOR) {
/*  9 */   VS_OUTPUT vout;
/* 10 */   vout.pos = pos;
/* 11 */   vout.color = color;
/* 12 */   return vout;
/* 13 */ }
```

The following performs a basic debugger test for the 3rd vertex in the triangle list:

```groovy
DEBUG pipeline DRAW_ARRAY AS TRIANGLE_LIST START_IDX 0 COUNT 6
    THREAD VERTEX_INDEX 2
        // Debugger starts at line 9. Inspect input variables.
        EXPECT LOCATION "simple_vs.hlsl" 9 "  VS_OUTPUT vout;"
￼        EXPECT LOCAL "pos.x" EQ -1.007874
￼        EXPECT LOCAL "pos.y" EQ 1.000000
￼        EXPECT LOCAL "pos.z" EQ 0.000000
￼        EXPECT LOCAL "color.x" EQ 1.000000
￼        EXPECT LOCAL "color.y" EQ 0.000000
￼        EXPECT LOCAL "color.z" EQ 0.000000
        // Step to line 10.
￼        STEP_IN
￼        EXPECT LOCATION "simple_vs.hlsl" 10 "  vout.pos = pos;"
        // Step to line 11 and read result of line 10.
￼        STEP_IN
        EXPECT LOCAL "vout.pos.x" EQ -1.007874
￼        EXPECT LOCAL "vout.pos.y" EQ 1.000000
￼        EXPECT LOCAL "vout.pos.z" EQ 0.000000
￼        EXPECT LOCATION "simple_vs.hlsl" 11 "  vout.color = color;"
        // Step to line 12 and read result of line 11.
￼        STEP_IN
￼        EXPECT LOCAL "vout.color.x" EQ 1.000000
￼        EXPECT LOCAL "vout.color.y" EQ 0.000000
￼        EXPECT LOCAL "vout.color.z" EQ 0.000000
￼        EXPECT LOCATION "simple_vs.hlsl" 12 "  return vout;"
￼        CONTINUE
    END
END
```

## Implementation

This section covers the design of how the debugger testing is implemented in Amber.

### Parsing

`Parser::ParseDebug()` starts by immediately calling `ParseRun()`, which parses the tokens that normally immediately follow a `RUN` command. On successful parse, `ParseRun()` appends a command into the `command_list_` vector. \
`ParseDebug()` then constructs a new `amber::debug::Script`, and parses the debugger command block. The `amber::debug::Script` is then assigned to the command at the back of the `command_list_` (added by `ParseRun()`).

### `amber::debug::Script`

`amber::debug::Script` implements the `amber::debug::Events` interface, and records the calls made on it.
These calls can be replayed to another `amber::debug::Events`, using the `amber::debug::Script::Run(Events*)` method.

### `amber::debug::Events`

The `amber::debug::Events` represents the `THREAD` commands in the Amber script, providing methods that set breakpoints for particular shader invocations.

`amber::debug::Events` is the interface implemented by `amber::debug::Script` for recording the parsed debugger script, and extended by the `amber::Engine::Debugger` interface, used to actually drive an engine debugger.

The `amber::debug::Events` interface has a number of `BreakOn`XXX`()` methods that have parameters for the shader invocation of interest (global invocation ID, vertex index, etc) and a `OnThread` function callback parameter.

The `OnThread` callback has the signature `void(amber::debug::Thread*)` which is called to control the debugger thread of execution and perform test verifications.

### `amber::debug::Thread`

`amber::debug::Thread` is the interface used to control a debugger thread of execution, and represents the script commands within the `THREAD` script blocks.

The following implementations of the `amber::debug::Thread` interface are returned by the `amber::debug::Script::BreakOn`XXX`()` methods:
* `amber::debug::Script` implements this interface to record the `THREAD` commands in the Amber script, which will be replayed when calling `amber::debug::Script::Run(amber::debug::Events*)`.
* `amber::Engine::Debugger` implementations will implement the `amber::debug::Thread` interface to actually control the debugger thread of execution and perform test verifications.

### `amber::Engine::Debugger`

The `amber::Engine::Debugger` interface extends the `amber::debug::Events` interface with a single `Flush()` method that ensures that all the previous event have been executed. `Flush()` returns a `amber::Result`, which holds the results of all the `amber::debug::Thread::Expect`XXX`()` calls.

The `amber::Engine::Debugger` interface can be obtained from the `amber::Engine` using the `amber::Engine::GetDebugger()` method.

### Debugger Execution

`amber::Executor::Execute()` drives the `amber::Engine::Debugger`:

* The before executing the first `amber::Command` that holds a `amber::debug::Script`, a `amber::Engine::Debugger` is obtained from the `amber::Engine`, and `amber::Engine::Debugger::Connect()` is called to create a connection to the Vulkan shader debugger.
* If the `amber::Command` holds a `amber::debug::Script`, then this script is executed on the `amber::Engine::Debugger` using the `amber::debug::Script::Run(amber::debug::Events *)` method, before the Vulkan command is executed.
* The command is then executed with `amber::Executor::ExecuteCommand()`
* Once the command has completed, all debugger threads are synchronized and debugger test results are collected with a call to `amber::Engine::Debugger::Flush()`.
* This process is repeated for all commands in the script.