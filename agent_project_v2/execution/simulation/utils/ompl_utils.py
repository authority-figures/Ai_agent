'''
Adopted from
https://github.com/StanfordVL/iGibson/blob/master/igibson/external/pybullet_tools/utils.py
'''

from __future__ import print_function

import pybullet as p
from collections import defaultdict, deque, namedtuple
from itertools import product, combinations, count

BASE_LINK = -1
MAX_DISTANCE = 0.001

def pairwise_link_collision(body1, link1, body2, link2=BASE_LINK,physicsClientId=0, max_distance=MAX_DISTANCE):  # 10000
    return len(p.getClosestPoints(bodyA=body1, bodyB=body2, distance=max_distance,
                                  linkIndexA=link1, linkIndexB=link2,physicsClientId=physicsClientId)) != 0  # getContactPoints

def pairwise_collision(body1, body2, **kwargs):
    if isinstance(body1, tuple) or isinstance(body2, tuple):
        body1, links1 = expand_links(body1,physicsClientId=kwargs.get('physicsClientId',0))
        body2, links2 = expand_links(body2,physicsClientId=kwargs.get('physicsClientId',0))
        return any_link_pair_collision(body1, links1, body2, links2, **kwargs)
    return body_collision(body1, body2, **kwargs)

def expand_links(body,physicsClientId=0):
    body, links = body if isinstance(body, tuple) else (body, None)
    if links is None:
        links = get_all_links(body,physicsClientId=physicsClientId)
    return body, links

def any_link_pair_collision(body1, links1, body2, links2=None, **kwargs):
    # TODO: this likely isn't needed anymore
    if links1 is None:
        links1 = get_all_links(body1,physicsClientId=kwargs.get('physicsClientId',0))
    if links2 is None:
        links2 = get_all_links(body2,physicsClientId=kwargs.get('physicsClientId',0))
    for link1, link2 in product(links1, links2):
        if (body1 == body2) and (link1 == link2):
            continue
        if pairwise_link_collision(body1, link1, body2, link2, **kwargs):
            # print('body {} link {} body {} link {}'.format(body1, link1, body2, link2))
            return True
    return False

def body_collision(body1, body2,physicsClientId=0, max_distance=MAX_DISTANCE):  # 10000
    return len(p.getClosestPoints(bodyA=body1, bodyB=body2, distance=max_distance,physicsClientId=physicsClientId)) != 0  # getContactPoints`

def get_self_link_pairs(body, joints, disabled_collisions=set(),physicsClientId=0, only_moving=True):
    moving_links = get_moving_links(body, joints,physicsClientId=physicsClientId)
    fixed_links = list(set(get_joints(body,physicsClientId=physicsClientId)) - set(moving_links))
    check_link_pairs = list(product(moving_links, fixed_links))
    if only_moving:
        check_link_pairs.extend(get_moving_pairs(body, joints,physicsClientId=physicsClientId))
    else:
        check_link_pairs.extend(combinations(moving_links, 2))
    check_link_pairs = list(
        filter(lambda pair: not are_links_adjacent(body, *pair,physicsClientId=physicsClientId), check_link_pairs))
    check_link_pairs = list(filter(lambda pair: (pair not in disabled_collisions) and
                                                (pair[::-1] not in disabled_collisions), check_link_pairs))
    return check_link_pairs

def get_moving_links(body, joints,physicsClientId=0):
    moving_links = set()
    for joint in joints:
        link = child_link_from_joint(joint)
        if link not in moving_links:
            moving_links.update(get_link_subtree(body, link,physicsClientId=physicsClientId))
    return list(moving_links)

def get_moving_pairs(body, moving_joints,physicsClientId=0):
    """
    Check all fixed and moving pairs
    Do not check all fixed and fixed pairs
    Check all moving pairs with a common
    """
    moving_links = get_moving_links(body, moving_joints,physicsClientId=physicsClientId)
    for link1, link2 in combinations(moving_links, 2):
        ancestors1 = set(get_joint_ancestors(body, link1,physicsClientId=physicsClientId)) & set(moving_joints)
        ancestors2 = set(get_joint_ancestors(body, link2,physicsClientId=physicsClientId)) & set(moving_joints)
        if ancestors1 != ancestors2:
            yield link1, link2


#####################################

JointInfo = namedtuple('JointInfo', ['jointIndex', 'jointName', 'jointType',
                                     'qIndex', 'uIndex', 'flags',
                                     'jointDamping', 'jointFriction', 'jointLowerLimit', 'jointUpperLimit',
                                     'jointMaxForce', 'jointMaxVelocity', 'linkName', 'jointAxis',
                                     'parentFramePos', 'parentFrameOrn', 'parentIndex'])

def get_joint_info(body, joint,physicsClientId=0):
    return JointInfo(*p.getJointInfo(body, joint,physicsClientId=physicsClientId))

def child_link_from_joint(joint):
    return joint  # link

def get_num_joints(body, physicsClientId=0):
    return p.getNumJoints(body,physicsClientId=physicsClientId)

def get_joints(body,physicsClientId=0):
    return list(range(get_num_joints(body,physicsClientId=physicsClientId)))

get_links = get_joints

def get_all_links(body,physicsClientId=0):
    return [BASE_LINK] + list(get_links(body,physicsClientId=physicsClientId))

def get_link_parent(body, link,physicsClientId=0):
    if link == BASE_LINK:
        return None
    return get_joint_info(body, link,physicsClientId=physicsClientId).parentIndex

def get_all_link_parents(body,physicsClientId=0):
    return {link: get_link_parent(body, link,physicsClientId=physicsClientId) for link in get_links(body, physicsClientId=physicsClientId)}

def get_all_link_children(body,physicsClientId=0):
    children = {}
    for child, parent in get_all_link_parents(body,physicsClientId=physicsClientId).items():
        if parent not in children:
            children[parent] = []
        children[parent].append(child)
    return children

def get_link_children(body, link,physicsClientId=0):
    children = get_all_link_children(body,physicsClientId=physicsClientId)
    return children.get(link, [])


def get_link_ancestors(body, link,physicsClientId=0):
    # Returns in order of depth
    # Does not include link
    parent = get_link_parent(body, link,physicsClientId=physicsClientId)
    if parent is None:
        return []
    return get_link_ancestors(body, parent,physicsClientId=physicsClientId) + [parent]


def get_joint_ancestors(body, joint,physicsClientId=0):
    link = child_link_from_joint(joint)
    return get_link_ancestors(body, link,physicsClientId=physicsClientId) + [link]

def get_link_descendants(body, link,physicsClientId=0, test=lambda l: True):
    descendants = []
    for child in get_link_children(body, link,physicsClientId=physicsClientId):
        if test(child):
            descendants.append(child)
            descendants.extend(get_link_descendants(body, child,physicsClientId=physicsClientId, test=test))
    return descendants


def get_link_subtree(body, link, **kwargs):
    return [link] + get_link_descendants(body, link, **kwargs)

def are_links_adjacent(body, link1, link2,physicsClientId=0):
    return (get_link_parent(body, link1,physicsClientId=physicsClientId) == link2) or \
           (get_link_parent(body, link2,physicsClientId=physicsClientId) == link1)

