from datetime import datetime
import threading


class SerialnoUtil:
    _id = 0
    _last_timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    _lock = threading.Lock()

    @classmethod
    def create_serial_no(cls, prefix: str = '', length: int = 20) -> str:
        """
        创建序列号
        Args:
            prefix: 前缀，如 'ORD_', 'TRD_' 等
            length: 序列号总长度（不含前缀）
        """
        with cls._lock:  # 使用 context manager 更安全
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            if timestamp == cls._last_timestamp:
                cls._id = (cls._id + 1) % 100000
            else:
                cls._last_timestamp = timestamp
                cls._id = 0

            sequence = str(cls._id).zfill(length - 14)
            return f"{prefix}{timestamp}{sequence}"


def test_serial_speed():
    import time
    from concurrent.futures import ThreadPoolExecutor
    
    start_time = time.perf_counter()
    count = 100000
    
    def generate():
        SerialnoUtil.create_serial_no()
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        list(executor.map(lambda _: generate(), range(count)))
    
    duration = time.perf_counter() - start_time
    print(f"生成 {count} 个序号用时: {duration:.2f} 秒")
    print(f"平均速度: {int(count/duration)} 个/秒")


if __name__ == "__main__":
    test_serial_speed()

