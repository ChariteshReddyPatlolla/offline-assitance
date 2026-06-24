import json, re

content = '{"type":"function","name":"web_search","parameters{"query":"hi"}}'

def find_json_objects(text: str) -> list:
    results = []
    stack = []
    start_idx = -1
    for i, char in enumerate(text):
        if char == '{':
            if not stack:
                start_idx = i
            stack.append(char)
        elif char == '}':
            if stack:
                stack.pop()
                if not stack:
                    results.append(text[start_idx:i+1])
    return results

if '"name"' in content and ('parameters' in content or 'args' in content or 'arguments' in content):
    json_objects = find_json_objects(content)
    print('Found objects:', json_objects)
    for json_str in json_objects:
        temp_str = json_str
        temp_str = re.sub(r'"(?:parameters|args|arguments)"?\s*:?\s*{', r'"arguments": {', temp_str)
        print('After regex:', temp_str)
        try:
            tool_data = json.loads(temp_str)
            print('Parsed JSON:', tool_data)
        except Exception as e:
            print('Error parsing JSON:', e)
else:
    print('Condition not met!')
