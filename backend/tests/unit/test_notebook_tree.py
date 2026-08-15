"""Pure-function checks on the notebook tree helpers.

The cycle and depth rules are the whole reason nesting is risky, so they
get tested without a database in the loop.
"""
import sys
sys.path.insert(0, "/home/lenin/Apps Developed/Socratic-ai/backend")

from api.routes.notebooks import _descendant_ids, _depth_of, _subtree_height


class NB:
    def __init__(self, id, parent_id):
        self.id = id
        self.parent_id = parent_id


#   1
#   +-- 2
#   |   +-- 4
#   |       +-- 5
#   +-- 3
#   6 (separate root)
tree = [NB(1, None), NB(2, 1), NB(3, 1), NB(4, 2), NB(5, 4), NB(6, None)]

ok = True


def check(label, got, want):
    global ok
    if got != want:
        ok = False
        print(f"FAIL {label}: got {got}, want {want}")
    else:
        print(f"pass {label}: {got}")


check("descendants of 1", _descendant_ids(tree, 1), {1, 2, 3, 4, 5})
check("descendants of 2", _descendant_ids(tree, 2), {2, 4, 5})
check("descendants of 5 (leaf)", _descendant_ids(tree, 5), {5})
check("descendants of 6 (lone root)", _descendant_ids(tree, 6), {6})

check("depth of root 1", _depth_of(tree, 1), 1)
check("depth of 2", _depth_of(tree, 2), 2)
check("depth of 5", _depth_of(tree, 5), 4)
check("depth of None (top level)", _depth_of(tree, None), 0)

check("height of subtree 1", _subtree_height(tree, 1), 4)
check("height of subtree 2", _subtree_height(tree, 2), 3)
check("height of leaf 5", _subtree_height(tree, 5), 1)

# The move that must be refused: 2 under 5, where 5 is 2's own descendant.
check("5 is a descendant of 2 -> move refused", 5 in _descendant_ids(tree, 2), True)
# The move that must be allowed: 2 under 6, an unrelated root.
check("6 is not a descendant of 2 -> move allowed", 6 in _descendant_ids(tree, 2), False)

# Depth arithmetic for a move: subtree 2 (height 3) under node 3 (depth 2)
# lands its deepest node at 5 - at the cap, so allowed; under node 4
# (depth 3) it would reach 6 and must be refused.
check("move 2 under 3 -> deepest level", _depth_of(tree, 3) + _subtree_height(tree, 2), 5)
check("move 2 under 4 -> deepest level", _depth_of(tree, 4) + _subtree_height(tree, 2), 6)

# A pre-existing cycle must not hang the depth walk.
cyclic = [NB(10, 11), NB(11, 10)]
check("cyclic input terminates", _depth_of(cyclic, 10), 2)

print("\nALL PASS" if ok else "\nFAILURES ABOVE")
sys.exit(0 if ok else 1)
