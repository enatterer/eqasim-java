import math

B = 200 #scenario count
min_z = None #idle task count
best_ys = [] #number of nodes
tasks_per_node = 15
low_bound = 1
upper_bound = 16

for y in range(low_bound, upper_bound):
    group = tasks_per_node * y #block size (or total number of tasks per job)
    A = group * math.ceil(B / group) #total number of tasks (across all jobs)
    z = A - B #idle task count
    if (min_z is None) or (z < min_z):
        min_z = z
        best_ys = [y]
    elif z == min_z:
        best_ys.append(y)

print(f"Best y: {best_ys}")
print(f"Minimum idle task count z: {min_z}")
print(f"Total Task across all jobs A: {tasks_per_node*best_ys[0] * math.ceil(B/(tasks_per_node*best_ys[0]))}")   