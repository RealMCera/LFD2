# Ghidra Jython script: privately export decompiler pseudocode for an imported
# Xbox 360 module. Script Manager category: L4D2 Research.
#@category L4D2 Research
#
# Headless script arguments:
#   <local-output-file> [max-functions=50] [start-address=first]
# Example:
#   -postScript ExportPseudocode.py C:\path\research\local\server_pseudo.txt 50 0x89DED900
#
# IMPORTANT: Ghidra output is approximation, NOT original/buildable C++.
# Keep the output in research/local/ (gitignored); never commit extracted code.

from ghidra.app.decompiler import DecompInterface
import os
import codecs


def log(message):
    print("[L4D2 decompiler] " + str(message))


args = getScriptArgs()
if len(args) < 1 or len(args) > 3:
    raise RuntimeError("Usage: ExportPseudocode.py <output.txt> [max-functions=50] [start-address]")

out_file = os.path.abspath(args[0])
limit = int(args[1]) if len(args) >= 2 else 50
if limit < 1 or limit > 10000:
    raise RuntimeError("max-functions must be between 1 and 10000")

start = None
if len(args) == 3:
    start = toAddr(args[2])
    if start is None:
        raise RuntimeError("Could not parse start address: " + args[2])

if os.path.exists(out_file):
    raise RuntimeError("Refusing to replace existing output: " + out_file)
folder = os.path.dirname(out_file)
if not os.path.isdir(folder):
    os.makedirs(folder)

decompiler = DecompInterface()
decompiler.setSimplificationStyle("decompile")
if not decompiler.openProgram(currentProgram):
    raise RuntimeError("Could not initialize Ghidra decompiler for current program")

attempted = 0
succeeded = 0
failed = 0
try:
    with codecs.open(out_file, "w", "utf-8") as dest:
        dest.write("Ghidra-generated pseudocode -- NOT original C++ source.\n")
        dest.write("Program: %s\n" % currentProgram.getName())
        dest.write("Language: %s\n\n" % currentProgram.getLanguageID())
        functions = currentProgram.getFunctionManager().getFunctions(True)
        while functions.hasNext() and attempted < limit:
            monitor.checkCancelled()
            f = functions.next()
            if start is not None and f.getEntryPoint().compareTo(start) < 0:
                continue
            attempted += 1
            addr = f.getEntryPoint()
            dest.write("\n" + "=" * 65 + "\n")
            dest.write("Function %s @ %s\n" % (f.getName(), addr))
            result = decompiler.decompileFunction(f, 45, monitor)
            if result.decompileCompleted() and result.getDecompiledFunction() is not None:
                dest.write(result.getDecompiledFunction().getC())
                dest.write("\n")
                succeeded += 1
            else:
                failed += 1
                dest.write("DECOMPILATION FAILED: %s\n" % result.getErrorMessage())
        dest.write("\nSUMMARY: attempted=%d decompiled=%d failed=%d\n" %
                   (attempted, succeeded, failed))
finally:
    decompiler.dispose()

log("Finished: attempted=%d decompiled=%d failed=%d" % (attempted, succeeded, failed))
log("Private output: " + out_file)
log("Do NOT put the generated game pseudocode on public GitHub.")
