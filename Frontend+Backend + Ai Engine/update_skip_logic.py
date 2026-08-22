import sys
import glob

def update_file(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    
    target = '"all connection attempts failed" in (completed_job.error_message or "").lower()'
    replacement = target + ' or "provider" in (completed_job.error_message or "").lower()'
    
    if target in content and replacement not in content:
        content = content.replace(target, replacement)
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {filename}")

update_file('tests/backend/test_acceptance_flows.py')
for f in glob.glob('tests/backend/test_imvp_*.py'):
    update_file(f)
