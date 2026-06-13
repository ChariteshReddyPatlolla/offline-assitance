def fix_indent():
    filepath = r"api\routes\chat.py"
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # The for loop starts at line 271 in our 1-indexed view, which is index 270.
    # We will look for "# Simple regex matches for low latency execution" which is line 278 (index 277).
    # And we'll indent everything until we see "if responses:" which is line 824 (index 823).
    
    start_idx = -1
    end_idx = -1
    
    for i, line in enumerate(lines):
        if line.startswith("        # Simple regex matches for low latency execution"):
            start_idx = i
            break
            
    for i in range(start_idx, len(lines)):
        if line.startswith("        if responses:"):
            # Actually line 824 might be `        if responses:`
            pass
            
    # Let's find end_idx explicitly
    for i in range(start_idx, len(lines)):
        if lines[i].startswith("        if responses:"):
            end_idx = i
            break
            
    if start_idx == -1 or end_idx == -1:
        print("Could not find start or end bounds.")
        return

    # Add 4 spaces to each line in the range
    for i in range(start_idx, end_idx):
        if lines[i].strip() != "":
            lines[i] = "    " + lines[i]

    with open(filepath, "w", encoding="utf-8") as f:
        f.writelines(lines)
        
    print("Successfully fixed indentation in chat.py")

fix_indent()
