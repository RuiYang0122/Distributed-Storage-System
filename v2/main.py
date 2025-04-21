import sys

FRE_PER_SLICING = 1800
MAX_DISK_NUM = (10 + 1)
MAX_DISK_SIZE = (16384 + 1)
MAX_REQUEST_NUM = (30000000 + 1)
MAX_OBJECT_NUM = (100000 + 1)
REP_NUM = 3 #副本个数，不是磁盘个数
EXTRA_TIME = 105

disk = [[0 for _ in range(MAX_DISK_SIZE)] for _ in range(MAX_DISK_NUM)]
disk_point = [1 for _ in range(MAX_DISK_NUM)]
_id = [0 for _ in range(MAX_OBJECT_NUM)]

current_request = 0
current_phase = 0


class Object:
    def __init__(self):
        self.replica = [0 for _ in range(REP_NUM + 1)] #object.replica[j]存储着object对象第j个副本的所在磁盘编号
        self.unit = [[] for _ in range(REP_NUM + 1)] #二维列表，object.unit[j]存储着object对象第j个副本（第一维）大小为size的对象的size个对象块在磁盘的编号（第二维）
        self.size = 0
        self.lastRequestPoint = 0 #用于获取上一次请求编号
        self.isDelete = False
        # 新增 read_done 属性，初始为空列表
        self.read_done = []


req_object_ids = [0] * MAX_REQUEST_NUM 
# 这个列表用于存储每个请求对应的对象 ID
# 例如，req_object_ids[5] 存储的是第 5 个请求对应的对象 ID

req_prev_ids = [0] * MAX_REQUEST_NUM
# 这个列表用于存储每个请求的上一个请求的 ID
# 例如，req_prev_ids[5] 存储的是第 5 个请求的上一个请求的 ID
# 通过这种方式可以构建请求的链表，方便遍历请求的历史记录

req_is_dones = [False] * MAX_REQUEST_NUM
# 这个列表用于标记每个请求是否已经完成
# 例如，req_is_dones[5] 为 True 表示第 5 个请求已经完成，为 False 表示未完成

objects = [Object() for _ in range(MAX_OBJECT_NUM)] #生成对象列表


#对齐时间戳
def timestamp_action():
    timestamp = input().split()[1]
    print(f"TIMESTAMP {timestamp}")
    sys.stdout.flush()


def do_object_delete(object_unit, disk_unit, size):
    for i in range(1, size + 1):
        disk_unit[object_unit[i]] = 0

def delete_action():
    n_delete = int(input())
    abortNum = 0 #中止请求数（取消的请求数量）
    for i in range(1, n_delete + 1):
        _id[i] = int(input()) #循环读取所有要删除的对象编号
    for i in range(1, n_delete + 1):
        delete_id = _id[i]
        currentId = objects[delete_id].lastRequestPoint #获取当前要删除对象的上一个（读取）请求编号
        #如果当前对象之前有过读取请求
        while currentId != 0:
            #且这个请求没有完成的话
            if not req_is_dones[currentId]:
                abortNum += 1 #中止数+1
            currentId = req_prev_ids[currentId] #继续循环检查，即检查这个请求的再上一个请求是否还有未完成的

    print(f"{abortNum}")

    for i in range(n_delete + 1):
        delete_id = _id[i]
        currentId = objects[delete_id].lastRequestPoint
        while currentId != 0:
            if not req_is_dones[currentId]:
                print(f"{currentId}") #上报中止的请求编号
            currentId = req_prev_ids[currentId] #继续循环检查，即检查这个请求的再上一个请求是否还有未完成的，并上报
        
        #删除对象及其另外两个副本（REP = 3）
        for j in range(1, REP_NUM + 1):
            do_object_delete(objects[delete_id].unit[j], disk[objects[delete_id].replica[j]], objects[delete_id].size)
        objects[delete_id].isDelete = True

    sys.stdout.flush()


def do_object_write(object_unit, disk_unit, size, object_id):
    current_write_point = 0 #当前对象已经写入的存储单元个数
    #V为磁盘容量
    for i in range(1, V + 1):
        if disk_unit[i] == 0:
            disk_unit[i] = object_id #如果当前存储单元空闲，则将该单元的值设置为 object_id，表示该单元已被当前对象占用
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
        # 初始化 read_done 属性，全部设为 False
        objects[write_id].read_done = [False] * size
        print(f"{write_id}")
        for j in range(1, REP_NUM + 1):
            print_next(f"{objects[write_id].replica[j]}")
            for k in range(1, size + 1):
                print_next(f" {objects[write_id].unit[j][k]}")
            print()
    sys.stdout.flush()


# 全局变量，用于存储当前时间片未完成的读取请求
current_requests = []


def read_action(last_action_is_read):
    global current_requests
    nRead = int(input())
    for i in range(1, nRead + 1):
        read_input = input().split()
        request_id = int(read_input[0])
        objectId = int(read_input[1])
        req_object_ids[request_id] = objectId
        req_prev_ids[request_id] = objects[objectId].lastRequestPoint
        objects[objectId].lastRequestPoint = request_id
        req_is_dones[request_id] = False
        current_requests.append(request_id)

    current_requests.sort()

    disk_actions = ["" for _ in range(N + 1)]
    disk_tokens = [G for _ in range(N + 1)]
    disk_prev_token = [0 for _ in range(N + 1)]
    completed_requests = []

    if not current_requests:
        for i in range(1, N + 1):
            print("#")
        print("0")
    else:
        block_requests = []
        # 按请求顺序遍历
        for req_id in current_requests:
            objectId = req_object_ids[req_id]
            obj = objects[objectId]
            for j in range(1, REP_NUM + 1):
                for block in obj.unit[j]:
                    if block != 0 and not obj.read_done[obj.unit[j].index(block)]:
                        block_requests.append((req_id, block))

        for req_id, block in block_requests:
            objectId = req_object_ids[req_id]
            obj = objects[objectId]
            block_read = False
            for _ in range(REP_NUM):
                best_disk = select_best_disk_for_block(block, obj, disk_point)
                if best_disk is not None and disk_tokens[best_disk] > 0:
                    current_point = disk_point[best_disk]
                    distance = (block - current_point) % V if block >= current_point else V - current_point + block
                    if distance > G and disk_tokens[best_disk] == G:
                        disk_actions[best_disk] = f"j {block}"
                        disk_tokens[best_disk] -= G
                        disk_prev_token[best_disk] = G
                        current_point = block
                        continue
                    else:
                        while current_point != block:
                            if disk_tokens[best_disk] >= 1:
                                disk_actions[best_disk] += "p"
                                disk_tokens[best_disk] -= 1
                                current_point = (current_point % V) + 1
                            else:
                                break
                        read_token_cost = get_read_token_cost(best_disk, disk_prev_token[best_disk], last_action_is_read)
                        if disk_tokens[best_disk] >= read_token_cost:
                            disk_actions[best_disk] += "r"
                            disk_tokens[best_disk] -= read_token_cost
                            disk_prev_token[best_disk] = read_token_cost
                            current_point = (current_point % V) + 1
                            block_read = True
                        
                            # 遍历所有副本，找到块所在的索引
                            for j in range(1, REP_NUM + 1):
                                if block in obj.unit[j]:
                                    index = obj.unit[j].index(block)
                                    obj.read_done[index] = True
                                    break

                    disk_point[best_disk] = current_point
                    if block_read:
                        break

        # 检查请求是否完成
        for req_id in current_requests[:]:
            objectId = req_object_ids[req_id]
            obj = objects[objectId]
            if all(obj.read_done):
                completed_requests.append(req_id)
                req_is_dones[req_id] = True
                # 重置 read_done 属性
                obj.read_done = [False] * obj.size

        # 输出磁头动作
        for i in range(1, N + 1):
            if not disk_actions[i]:
                print("#")
            else:
                print(f"{disk_actions[i]}"+ "#")

        # 输出完成的请求数量和编号
        print(f"{len(completed_requests)}")
        for req_id in completed_requests:
            print(f"{int(req_id)}")

        # 从全局请求列表中移除已完成的请求
        current_requests = [req_id for req_id in current_requests if req_id not in completed_requests]

    sys.stdout.flush()

def select_best_disk_for_block(block, obj, disk_point):
    best_disk = 1
    min_distance = float('inf')
    for j in range(1, REP_NUM + 1):
        if block in obj.unit[j]:
            current_disk_point = disk_point[obj.replica[j]]
            if block >= current_disk_point:
                distance = block - current_disk_point
            else:
                distance = V - current_disk_point + block
            if distance < min_distance:
                min_distance = distance
                best_disk = obj.replica[j]
    return best_disk



def get_read_token_cost(disk_num, prev_token,last_action_is_read):
    """
    计算读取操作消耗的令牌数。
    :param disk_num: 磁盘编号
    :param prev_token: 上一次动作消耗的令牌数
    :return: 本次读取操作消耗的令牌数
    """
    # 如果上一次动作不是 "Read" 或者是第一个时间片首次 "Read"，消耗 64 个令牌
    if not last_action_is_read[disk_num]:
        last_action_is_read[disk_num] = True
        return 64
    else:
        return max(16, int(prev_token * 0.8) + (1 if prev_token * 0.8 % 1 != 0 else 0))


def print_next(message):
    print(f"{message}", end="")


if __name__ == '__main__':
    user_input = input().split()
    T = int(user_input[0]) # 时间片数T+105
    M = int(user_input[1]) # 对象标签数
    N = int(user_input[2]) # 硬盘个数
    V = int(user_input[3]) # 硬盘容量（硬盘中单元个数，每个单元存储一个数字）
    G = int(user_input[4]) # 每个磁头disk_point在每个时间片内最多消耗的令牌数
    # skip preprocessing
    for item in range(1, M * 3 + 1):
        input() # 对象标签输入，————待处理———— 
    print("OK")
    sys.stdout.flush()

    # 在 main 函数中定义 last_action_is_read
    last_action_is_read = [False] * N

    #将每个硬盘的磁头disk_point位置初始化为1，disk_point[i]表示第i个硬盘的磁头位置
    for item in range(1, N + 1):
        disk_point[item] = 1
    for item in range(1, T + EXTRA_TIME + 1):
        timestamp_action()
        delete_action()
        write_action()
        read_action(last_action_is_read)
