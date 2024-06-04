import os
import subprocess
import json
import argparse

stack_path = '.stack'

def load_branch_tree():
    if not os.path.exists(stack_path):
        return {}
    with open(stack_path, 'r') as f:
        return json.load(f)

def save_branch_tree(tree):
    with open(stack_path, 'w') as f:
        json.dump(tree, f)

def run_command(command):
    process = subprocess.Popen(command.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, error = process.communicate()
    return output.decode('utf-8')

def has_origin():
    return run_command('git remote get-url origin').strip() != ''

def current():
    return run_command('git branch --show-current').strip()

def pull():
    if has_origin():
        run_command('git pull')

def checkout(branch):
    if current() != branch:
        run_command(f'git checkout {branch}')

def create(branch_name):
    run_command(f'git checkout -b {branch_name}')

def rebase(branch):
    run_command(f'git rebase {branch}')

def merge(branch):
    run_command(f'git merge {branch}')

def restack_branch(target, base, should_rebase=True):
    # Checkout the base branch and pull
    checkout(base)
    pull()

    # Checkout the target branch and pull
    checkout(target)
    pull()
    
    # Rebase the target branch on top of the base branch
    if should_rebase:
        rebase(base)
    else:
        merge(base)

def fetch():
    if has_origin():
        run_command('git fetch')

def branch_exists(branch):
    branches = run_command('git branch').split()
    return branch in branches

def parent(branch):
    tree = load_branch_tree()
    if branch not in tree:
        return None
    return tree[branch]

def reparent_children(branch, new_parent):
    tree = load_branch_tree()
    for child, parent in tree.items():
        if parent == branch:
            tree[child] = new_parent
    save_branch_tree(tree)

def restack(should_rebase=True):
    backstack = []
    tree = load_branch_tree()
    fetch()
    initial = current()
    next = current()
    while next in tree:
        backstack.append(next)
        next = parent(next)
    if next is not None:
        backstack.append(next)

    # Print out a preview
    print(f'Restack preview ({"Merge" if not should_rebase else "Rebase"}):')
    for branch in backstack[::-1]:
        base = parent(branch)
        if base is not None:
            if not branch_exists(branch):
                print(f'  {branch} <- {base} (branch deleted)')
            else:
                print(f'  {branch} <- {base}')
    
    should_continue = input('Continue? (y/n) ').lower()[0] == 'y'
    if not should_continue:
        print('Aborting restack')
        return
    
    for branch in backstack[::-1]:
        base = parent(branch)
        if base is not None:
            # If the branch no longer exists, reparent it
            if not branch_exists(branch):
                print(f'Reparenting {branch}\'s children to {base}')
                reparent_children(branch, base)
            else:
                print(f'Restacking {branch} on top of {base}')
                restack_branch(branch, base, should_rebase)
    # Return to the initial branch
    checkout(initial)
    print(f'Restack complete. You are on {current()} now.')
    

parser = argparse.ArgumentParser()
parser.add_argument('--rebase', action='store_true')
parser.add_argument('--stack-path', default='.stack')
args = parser.parse_args()

stack_path = args.stack_path
restack(args.rebase)