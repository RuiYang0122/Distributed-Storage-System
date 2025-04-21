import sys

FRE_PER_SLICING = 1800
MAX_DISK_NUM = (10 + 1)
MAX_DISK_SIZE = (16384 + 1)
MAX_REQUEST_NUM = (30000000 + 1)
MAX_OBJECT_NUM = (100000 + 1)
REP_NUM = 3 
EXTRA_TIME = 105

disk = [[0 for _ in range(MAX_DISK_SIZE)] for _ in range(MAX_DISK_NUM)]
disk_point = [0 for _ in range(MAX_DISK_NUM)]
_id = [0 for _ in range(MAX_OBJECT_NUM)]

current_request = 0
current_phase = 0
read_requests = []  # 新增：存储所有读取请求的列表

class Object:
    def __init__(self):
        self.replica = [0 for _ in range(REP_NUM + 1)]
        self.unit = [[] for _ in range(REP_NUM + 1)]
        self.size = 0
        self.lastRequestPoint = 0 
        self.isDelete = False

class Disk:
    def __init__(self):
        self.is_processing = False  # 新增：磁盘是否正在处理请求
        self.current_request = 0
        self.current_phase = 0
        # 新增：存储当前磁盘处理的请求对应的对象副本索引
        self.replica_index = 0

req_object_ids = [0] * MAX_REQUEST_NUM
req_prev_ids = [0] * MAX_REQUEST_NUM
req_is_dones = [False] * MAX_REQUEST_NUM

objects = [Object() for _ in range(MAX_OBJECT_NUM)] 
disks = [Disk() for _ in range(MAX_DISK_NUM)]  # 新增：磁盘对象列表

def do_object_delete(object_unit, disk_unit, size):
    for i in range(1, size + 1):
        disk_unit[object_unit[i]] = 0

def timestamp_action():
    timestamp = input().split()[1]
    print(f"TIMESTAMP {timestamp}")
    sys.stdout.flush()

def delete_action():
    n_delete = int(input())
    abortNum = 0 
    for i in range(1, n_delete + 1):
        _id[i] = int(input())
    for i in range(1, n_delete + 1):
        delete_id = _id[i]
        currentId = objects[delete_id].lastRequestPoint 
        while currentId != 0:
            if not req_is_dones[currentId]:
                abortNum += 1
            currentId = req_prev_ids[currentId]

    print(f"{abortNum}")
    for i in range(n_delete + 1):
        delete_id = _id[i]
        currentId = objects[delete_id].lastRequestPoint
        while currentId != 0:
            if not req_is_dones[currentId]:
                print(f"{currentId}")
            currentId = req_prev_ids[currentId]
        for j in range(1, REP_NUM + 1):
            do_object_delete(objects[delete_id].unit[j], disk[objects[delete_id].replica[j]], objects[delete_id].size)
        objects[delete_id].isDelete = True
    sys.stdout.flush()

def do_object_write(object_unit, disk_unit, size, object_id):
    current_write_point = 0
    for i in range(1, V + 1):
        if disk_unit[i] == 0:
            disk_unit[i] = object_id
            current_write_point += 1
            object_unit[current_write_point] = i
            if current_write_point == size:
                break
    assert (current_write_point == size)

def write_action():
    n_write = int(input())
    for i in range(1, n_write + 1):
        write_input = input().split()
        write_id = int(write_input[0])
        size = int(write_input[1])
        objects[write_id].lastRequestPoint = 0
        for j in range(1, REP_NUM + 1):
            objects[write_id].replica[j] = (write_id + j) % N + 1
            objects[write_id].unit[j] = [0 for _ in range(size + 1)]
            objects[write_id].size = size
            objects[write_id].isDelete = False
            do_object_write(objects[write_id].unit[j], disk[objects[write_id].replica[j]], size, write_id)
        print(f"{write_id}")
        for j in range(1, REP_NUM + 1):
            print_next(f"{objects[write_id].replica[j]}")
            for k in range(1, size + 1):
                print_next(f" {objects[write_id].unit[j][k]}")
            print()
    sys.stdout.flush()

def print_next(message):
    print(f"{message}", end="")


def read_action():
    request_id = 0
    global read_requests
    global disks
    nRead = int(input())
    for i in range(1, nRead + 1):
        read_input = input().split()
        request_id = int(read_input[0])
        objectId = int(read_input[1])
        req_object_ids[request_id] = objectId
        req_prev_ids[request_id] = objects[objectId].lastRequestPoint
        objects[objectId].lastRequestPoint = request_id
        req_is_dones[request_id] = False
        read_requests.append(request_id)

    # 若 read_requests 为空，输出对应信息
    if not read_requests:
        for _ in range(1, N + 1):
            print("#")
        print("0")
        
    else:
        # 倒着分配请求给空闲磁盘
        requests_to_remove = []
        for i in range(len(read_requests) - 1, -1, -1):
            request_id = int(read_requests[i])
            objectId = int(req_object_ids[request_id])
            obj = objects[objectId]
            for disk_id in range(1, N + 1):
                # 检查磁盘是否空闲且有该请求对象的副本
                if disks[disk_id].is_processing == False and disk_id in obj.replica:
                    # 获取当前磁盘是对象的第几个副本
                    replica_index = int(obj.replica.index(disk_id)) + 1
                    disks[disk_id].is_processing = True
                    disks[disk_id].current_request = request_id
                    disks[disk_id].current_phase = 0
                    # 存储副本索引
                    disks[disk_id].replica_index = replica_index
                    requests_to_remove.append(request_id)
                    break


        # 从 read_requests 中移除已分配的请求
        for request_id in requests_to_remove:
            read_requests.remove(request_id)

        completed_requests = []
        for disk_id in range(1, N + 1):
            if disks[disk_id].is_processing:
                disks[disk_id].current_phase += 1
                current_request = int(disks[disk_id].current_request)
                current_phase = int(disks[disk_id].current_phase)
                objectId = int(req_object_ids[current_request])
                # 获取副本索引
                replica_index = int(disks[disk_id].replica_index)
                if current_phase % 2 == 1:
                    # 使用副本索引
                    print(f"j {objects[objectId].unit[replica_index][int(current_phase / 2 + 1)]}")
                else:
                    print("r#")
                
                if disks[disk_id].current_phase == objects[objectId].size * 2 :
                    disks[disk_id].is_processing = False
                    disks[disk_id].current_request = 0
                    disks[disk_id].current_phase = 0
                    disks[disk_id].replica_index = 0
                    if not objects[objectId].isDelete:
                        completed_requests.append(current_request)
                        req_is_dones[current_request] = True
            else:
                print("#")

        

        if completed_requests:
            print(int(len(completed_requests)))
            for request_id in completed_requests:
                print(f"{request_id}")
                req_is_dones[request_id] = True

        else:
            print("0")

    sys.stdout.flush()

if __name__ == '__main__':
    user_input = input().split()
    T = int(user_input[0]) # 时间片数T+105
    M = int(user_input[1]) # 对象标签数
    N = int(user_input[2]) # 硬盘个数
    V = int(user_input[3]) # 硬盘容量（硬盘中单元个数，每个单元存储一个数字）
    G = int(user_input[4]) # 每个磁头disk_point在每个时间片内最多消耗的令牌数
    # skip preprocessing
    for item in range(1, M * 3 + 1):
        input()
    print("OK")
    sys.stdout.flush()
    for item in range(1, N + 1):
        disk_point[item] = 1
    for item in range(1, T + EXTRA_TIME + 1):
        timestamp_action()
        delete_action()
        write_action()
        read_action()
