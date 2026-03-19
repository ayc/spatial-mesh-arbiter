import os
import glob
import re

sketch_dir = "/home/ayc/Documents/ayc/spatial-mesh-arbiter/docs-game-compiler/ability-sketches"
files = glob.glob(os.path.join(sketch_dir, "*.md"))

def extract_sections(text):
    obs = ""
    req = ""
    
    # regex to find sections
    obs_match = re.search(r'## Observable Behavior(.*?)##', text, re.DOTALL)
    if obs_match:
        obs = obs_match.group(1).strip()
        
    req_match = re.search(r'## Engine Primitives Required(.*?)##', text, re.DOTALL)
    if req_match:
        req = req_match.group(1).strip()
        
    return obs, req

all_obs = []
all_req = []

for f in files:
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
        obs, req = extract_sections(content)
        if obs and "TODO" not in obs:
            all_obs.append(obs)
        if req and "TODO" not in req:
            all_req.append(req)

print(f"Parsed {len(files)} files")
print(f"Found {len(all_obs)} distinct Observable Behaviors")
print(f"Found {len(all_req)} distinct Engine Primitives Required")

with open('aggregated_text.txt', 'w', encoding='utf-8') as out:
    out.write("\n=== OBSERVABLE BEHAVIORS ===\n")
    out.write("\n".join(all_obs))
    out.write("\n=== ENGINE PRIMITIVES REQUIRED ===\n")
    out.write("\n".join(all_req))
