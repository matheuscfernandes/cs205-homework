import sys
import os.path
sys.path.append(os.path.join('..', 'util'))

import set_compiler
set_compiler.install()

import pyximport
pyximport.install()

import numpy as np
from timer import Timer
from animator import Animator
from physics import update, preallocate_locks

num_threads=4

def less_msb(x, y):
    # From: https://en.wikipedia.org/wiki/Z-order_curve
    return x < y and x < (x ^ y)

def cmp_zorder(a1, b1):
    # From: https://en.wikipedia.org/wiki/Z-order_curve
    j = 0
    k = 0
    x = 0
    a=a1[1]
    b=b1[1]
    for k in range(2):
        y = a[k] ^ b[k]
        if less_msb(x, y):
            j = k
            x = y
    return a[j] - b[j]

def randcolor():
    return np.random.uniform(0.0, 0.89, (3,)) + 0.1

if __name__ == '__main__':
    num_balls = 10000
    radius = 0.002

    # num_balls = 10
    # radius = 0.05
    positions = np.random.uniform(0 + radius, 1 - radius,
                                  (num_balls, 2)).astype(np.float32)

    # make a hole in the center
    while True:
        distance_from_center = np.sqrt(((positions - 0.5) ** 2).sum(axis=1))
        mask = (distance_from_center < 0.25)
        num_close_to_center = mask.sum()
        if num_close_to_center == 0:
            # everything is out of the center
            break
        positions[mask, :] = np.random.uniform(0 + radius, 1 - radius,
                                               (num_close_to_center, 2)).astype(np.float32)

    velocities = np.random.uniform(-0.25, 0.25,
                                   (num_balls, 2)).astype(np.float32)

    # Initialize grid indices:
    #
    # Each square in the grid stores the index of the object in that square, or
    # -1 if no object.  We don't worry about overlapping objects, and just
    # store one of them.
    grid_spacing = radius / np.sqrt(2.0) # size of each individual grid
    grid_size = int((1.0 / grid_spacing) + 1) # number of grids inside domain
    grid = - np.ones((grid_size, grid_size), dtype=np.uint32)
    grid[(positions[:, 0] / grid_spacing).astype(int),
         (positions[:, 1] / grid_spacing).astype(int)] = np.arange(num_balls)
    
    # A matplotlib-based animator object
    animator = Animator(positions, radius * 2)

    # simulation/animation time variablees
    physics_step = 1.0 / 100  # estimate of real-time performance of simulation
    anim_step = 1.0 / 30  # FPS
    total_time = 0

    frame_count = 0

    # SUBPROBLEM 4: uncomment the, code below.
    # preallocate locks for objects
    locks_ptr = preallocate_locks(num_balls)

    while True:
        with Timer() as t:
            update(positions, velocities, grid,
                   radius, grid_spacing, locks_ptr,
                   physics_step, num_threads)

        # udpate our estimate of how fast the simulator runs
        physics_step = 0.9 * physics_step + 0.1 * t.interval
        total_time += t.interval

        frame_count += 1
        if total_time > anim_step:
            animator.update(positions)
            print("{} simulation frames per second".format(frame_count / total_time))
            frame_count = 0
            total_time = 0

            # SUBPROBLEM 3: sort objects by location.  Be sure to update the
            # grid if objects' indices change!  Also be sure to sort the
            # velocities with their object positions!

            # OBTAIN ARRAY OF GRID POSITIONS FOR EACH BALL, MAKE SURE IT 
            # IS DEFINED AS AN INTEGER
            gridPositions = (positions / grid_spacing).astype(int)

            # POSISTION MATRIX INCLUDING AN INDIVIDUALIZED INDEX FOR EACH
            # POSITION WITHIN THE GRID POINT. THIS IS PREPARED SO THAT IT
            # CAN BE SORTED BY THE SORT FUNCTION
            zorderPositions = zip(range(len(gridPositions)), gridPositions)

            # SORTING FUNCTION USING THE MORTON ORDERING DESCRIBED BY WIKIPEDIA
            zorderPositions.sort(cmp_zorder)
            # OBTAIN THE INDEX FROM THE ORDERING
            zorder = [x[0] for x in zorderPositions]

            # RE-ODER THE POSITIONS AND VELOCITIES BASED ON THE Z-ORDERING
            positions = positions[zorder]
            velocities = velocities[zorder]
            
            # MAKING SURE THAT THE POSITION OF EACH BALL IS WITHIN THE BOUNDS OF THE DOMAIN
            newPositions = np.array(filter(lambda x: x[0] > 0 and x[1] < 1, positions))

            # RECREATE THE REORDERD GRID BASED ON THE POINTS WITHINT THE SPACE
            grid = - np.ones((grid_size, grid_size), dtype=np.uint32)
            grid[(newPositions[:, 0] / grid_spacing).astype(int),
                 (newPositions[:, 1] / grid_spacing).astype(int)] = np.arange(len(newPositions))


