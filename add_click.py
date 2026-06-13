import re

def refactor():
    filepath = r"api\routes\chat.py"
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Add to the any([...]) pre-check loop
    target_1 = r"            re.match(r'^close\s+(.+)$', ml),"
    replacement_1 = r"            re.match(r'^(?:click\s+(?:on\s+)?|go\s+to\s+)(.+)$', ml)," + "\n" + target_1
    if target_1 in content:
        content = content.replace(target_1, replacement_1)
    else:
        print("Failed 1")
        return

    # 2. Add to regex assignments in execution loop
    target_2 = r"        close_app_match = re.match(r'^close\s+(.+)$', msg_lower)"
    replacement_2 = r"        click_match = re.match(r'^(?:click\s+(?:on\s+)?|go\s+to\s+)(.+)$', msg_lower)" + "\n" + target_2
    if target_2 in content:
        content = content.replace(target_2, replacement_2)
    else:
        print("Failed 2")
        return

    # 3. Add to execution block
    target_3 = r"        elif this_match:"
    replacement_3 = """        elif click_match:
            link_text = click_match.group(1).strip()
            try:
                import pyautogui
                import time
                # Yield focus back to the underlying window first
                pyautogui.hotkey("alt", "tab")
                time.sleep(0.2)
                
                # Simulate Ctrl+F, type text, Esc, Enter to natively click a link by text on screen
                pyautogui.hotkey("ctrl", "f")
                time.sleep(0.1)
                pyautogui.write(link_text, interval=0.01)
                time.sleep(0.2)
                pyautogui.press("esc")
                time.sleep(0.1)
                pyautogui.press("enter")
                
                fast_path_response = f"Clicked on '{link_text}' (Fast-path)."
            except Exception as e:
                logger.warning("Fast-path click link failed: %s", e)

""" + target_3

    if target_3 in content:
        content = content.replace(target_3, replacement_3)
    else:
        print("Failed 3")
        return

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
        
    print("Successfully added click_match")

refactor()
