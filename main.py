from dataclasses import dataclass
from enum import Enum


@dataclass
class Equipment:
    id: int
    name: str
    room: str
    status: str

    def __post_init__(self):
        if not isinstance(self.id, int) or isinstance(self.id, bool) or self.id <= 0:
            raise ValueError("Инвентарный номер должен быть положительным целым числом")


def division_hash(key, capacity):
    return key % capacity


def mixed_hash(key, capacity):
    return ((7 * key + 3) % 101) % capacity


@dataclass
class DistributionResult:
    addresses: list
    occupied: int
    empty: int
    collisions: int
    maximum: int
    load_factor: float


def analyze_distribution(keys, capacity, hash_function):
    counts = [0] * capacity
    addresses = []
    collisions = 0
    for key in keys:
        address = hash_function(key, capacity)
        addresses.append((key, address))
        if counts[address] > 0:
            collisions += 1
        counts[address] += 1
    occupied = 0
    maximum = 0
    for count in counts:
        if count > 0:
            occupied += 1
        if count > maximum:
            maximum = count
    return DistributionResult(addresses, occupied, capacity - occupied, collisions, maximum, len(keys) / capacity)


class ChainNode:
    def __init__(self, equipment):
        self.data = equipment
        self.next = None


class ChainedHashTable:
    def __init__(self, capacity=13):
        self.capacity = capacity
        self.size = 0
        self.buckets = [None] * capacity

    def insert(self, equipment):
        if not isinstance(equipment, Equipment):
            raise TypeError("Ожидается запись Equipment")
        index = division_hash(equipment.id, self.capacity)
        current = self.buckets[index]
        if current is None:
            self.buckets[index] = ChainNode(equipment)
            self.size += 1
            return True
        while current:
            if current.data.id == equipment.id:
                return False
            if current.next is None:
                break
            current = current.next
        current.next = ChainNode(equipment)
        self.size += 1
        return True

    def search(self, equipment_id):
        index = division_hash(equipment_id, self.capacity)
        current = self.buckets[index]
        comparisons = 0
        while current:
            comparisons += 1
            if current.data.id == equipment_id:
                return current.data, comparisons
            current = current.next
        return None, comparisons

    def update(self, equipment_id, room=None, status=None):
        record, _ = self.search(equipment_id)
        if record is None:
            return False
        if room is not None:
            record.room = room
        if status is not None:
            record.status = status
        return True

    def delete(self, equipment_id):
        index = division_hash(equipment_id, self.capacity)
        current = self.buckets[index]
        previous = None
        while current:
            if current.data.id == equipment_id:
                if previous is None:
                    self.buckets[index] = current.next
                else:
                    previous.next = current.next
                self.size -= 1
                return True
            previous = current
            current = current.next
        return False

    def contains(self, equipment_id):
        record, _ = self.search(equipment_id)
        return record is not None

    def load_factor(self):
        return self.size / self.capacity

    def display(self):
        lines = []
        for index, node in enumerate(self.buckets):
            values = []
            current = node
            while current:
                values.append(str(current.data.id))
                current = current.next
            lines.append(f"{index}: {' → '.join(values) if values else '—'}")
        return "\n".join(lines)

    def rehash(self, new_capacity):
        old_buckets = self.buckets
        self.capacity = new_capacity
        self.buckets = [None] * new_capacity
        old_size = self.size
        self.size = 0
        for node in old_buckets:
            current = node
            while current:
                self.insert(current.data)
                current = current.next
        self.size = old_size


class ProbeStrategy(Enum):
    LINEAR = "Линейное пробирование"
    QUADRATIC = "Квадратичное пробирование"
    DOUBLE = "Двойное хеширование"


EMPTY = object()
DELETED = object()


class OpenAddressHashTable:
    def __init__(self, capacity=13, strategy=ProbeStrategy.LINEAR, auto_resize=False):
        self.capacity = capacity
        self.size = 0
        self.deleted_count = 0
        self.data = [EMPTY] * capacity
        self.strategy = strategy
        self.auto_resize = auto_resize

    def _index(self, key, attempt):
        home = division_hash(key, self.capacity)
        if self.strategy == ProbeStrategy.LINEAR:
            return (home + attempt) % self.capacity
        if self.strategy == ProbeStrategy.QUADRATIC:
            return (home + attempt * attempt) % self.capacity
        step = 1 + key % (self.capacity - 1)
        return (home + attempt * step) % self.capacity

    def insert(self, equipment):
        if not isinstance(equipment, Equipment):
            raise TypeError("Ожидается запись Equipment")
        if self.auto_resize and (self.size + 1) / self.capacity > 0.70:
            self.rehash(next_prime(self.capacity * 2))
        first_deleted = None
        for attempt in range(self.capacity):
            index = self._index(equipment.id, attempt)
            cell = self.data[index]
            if isinstance(cell, Equipment):
                if cell.id == equipment.id:
                    return False, attempt + 1, index
            elif cell is DELETED:
                if first_deleted is None:
                    first_deleted = index
            else:
                target = first_deleted if first_deleted is not None else index
                self.data[target] = equipment
                self.size += 1
                if first_deleted is not None:
                    self.deleted_count -= 1
                return True, attempt + 1, target
        if first_deleted is not None:
            self.data[first_deleted] = equipment
            self.size += 1
            self.deleted_count -= 1
            return True, self.capacity, first_deleted
        return False, self.capacity, -1

    def search(self, equipment_id):
        visited = []
        for attempt in range(self.capacity):
            index = self._index(equipment_id, attempt)
            visited.append(index)
            cell = self.data[index]
            if cell is EMPTY:
                return None, visited, len(visited)
            if isinstance(cell, Equipment) and cell.id == equipment_id:
                return cell, visited, len(visited)
        return None, visited, len(visited)

    def update(self, equipment_id, room=None, status=None):
        record, _, _ = self.search(equipment_id)
        if record is None:
            return False
        if room is not None:
            record.room = room
        if status is not None:
            record.status = status
        return True

    def delete(self, equipment_id):
        record, visited, _ = self.search(equipment_id)
        if record is None:
            return False
        index = visited[-1]
        self.data[index] = DELETED
        self.size -= 1
        self.deleted_count += 1
        return True

    def contains(self, equipment_id):
        record, _, _ = self.search(equipment_id)
        return record is not None

    def load_factor(self):
        return self.size / self.capacity

    def used_factor(self):
        return (self.size + self.deleted_count) / self.capacity

    def rehash(self, new_capacity):
        old_data = self.data
        self.capacity = new_capacity
        self.data = [EMPTY] * new_capacity
        old_size = self.size
        self.size = 0
        self.deleted_count = 0
        for cell in old_data:
            if isinstance(cell, Equipment):
                self.insert(cell)
        self.size = old_size
        self.deleted_count = 0

    def display(self):
        lines = []
        for index, cell in enumerate(self.data):
            if isinstance(cell, Equipment):
                value = str(cell.id)
            elif cell is DELETED:
                value = "DELETED"
            else:
                value = "—"
            lines.append(f"{index}: {value}")
        return "\n".join(lines)


def is_prime(number):
    if number < 2:
        return False
    divisor = 2
    while divisor * divisor <= number:
        if number % divisor == 0:
            return False
        divisor += 1
    return True


def next_prime(number):
    candidate = max(2, number)
    while not is_prime(candidate):
        candidate += 1
    return candidate


INITIAL_RECORDS = [
    Equipment(26, "Проектор", "A-201", "Свободно"),
    Equipment(39, "3D-принтер", "A-305", "Обслуживание"),
    Equipment(52, "Осциллограф", "B-214", "Свободно"),
    Equipment(14, "Ноутбук", "A-108", "Выдано"),
    Equipment(27, "Маршрутизатор", "B-214", "Свободно"),
    Equipment(40, "Набор микроконтроллеров", "A-305", "Выдано"),
    Equipment(16, "Веб-камера", "A-108", "Свободно"),
    Equipment(29, "Графический планшет", "A-201", "Обслуживание"),
    Equipment(42, "Лазерный принтер", "A-108", "Свободно"),
]


def run_demo():
    print("РЕЕСТР УЧЕБНОГО ОБОРУДОВАНИЯ")
    print("\n1. Анализ хеш-функций")
    keys = [item.id for item in INITIAL_RECORDS]
    for name, function in (("Метод деления", division_hash), ("Смешанная функция", mixed_hash)):
        result = analyze_distribution(keys, 13, function)
        print(f"{name}: занято {result.occupied}, пусто {result.empty}, "
              f"коллизий {result.collisions}, максимум в бакете {result.maximum}, "
              f"заполнение {result.load_factor:.3f}")

    print("\n2. Метод цепочек")
    chained = ChainedHashTable(13)
    for item in INITIAL_RECORDS:
        chained.insert(Equipment(item.id, item.name, item.room, item.status))
    print(chained.display())
    for key in (42, 91):
        record, comparisons = chained.search(key)
        print(f"Поиск {key}: {'найден' if record else 'не найден'}, сравнений: {comparisons}")
    print("Повторная вставка 27:", chained.insert(Equipment(27, "Дубликат", "X", "X")))
    chained.update(27, "B-310", "Выдано")
    chained.insert(Equipment(195, "Документ-камера", "B-210", "Свободно"))
    chained.delete(39)
    chained.insert(Equipment(351, "VR-шлем", "B-212", "Свободно"))
    print("После изменения и удаления:")
    print(chained.display())

    print("\n3. Открытая адресация")
    tables = []
    for strategy in ProbeStrategy:
        table = OpenAddressHashTable(13, strategy)
        for item in INITIAL_RECORDS:
            table.insert(Equipment(item.id, item.name, item.room, item.status))
        tables.append(table)
        print(f"\n{strategy.value}:")
        print(table.display())
        for key in (42, 91):
            record, path, probes = table.search(key)
            print(f"Поиск {key}: путь {' → '.join(map(str, path))}, "
                  f"проб: {probes}, результат: {'найден' if record else 'не найден'}")

        table.insert(Equipment(195, "Документ-камера", "B-210", "Свободно"))
        table.delete(39)
        record, path, probes = table.search(195)
        print(f"Поиск 195 после удаления 39: {' → '.join(map(str, path))}; проб: {probes}")
        table.insert(Equipment(351, "VR-шлем", "B-212", "Свободно"))
        print("После вставки 351:")
        print(table.display())

    print("\n4. Автоматическое расширение")
    table = OpenAddressHashTable(13, ProbeStrategy.LINEAR, auto_resize=False)
    for item in INITIAL_RECORDS:
        table.insert(Equipment(item.id, item.name, item.room, item.status))
    table.insert(Equipment(195, "Документ-камера", "B-210", "Свободно"))
    table.delete(39)
    table.insert(Equipment(351, "VR-шлем", "B-212", "Свободно"))
    table.auto_resize = True
    table.insert(Equipment(54, "Набор датчиков", "A-305", "Свободно"))
    print(f"capacity={table.capacity}, size={table.size}, deleted_count={table.deleted_count}")
    print(table.display())

    print("\n5. Экспериментальное сравнение (m=101)")
    print("Заполнение | Стратегия | Коллизии | Среднее проб | Макс. проб | "
          "Успешный поиск | Неуспешный поиск | Макс. цепочка | Пустые")
    for fill in (0.25, 0.50, 0.70, 0.85):
        count = int(101 * fill)
        ids = [i * 101 + (i % 17) + 1 for i in range(count)]
        for strategy in ProbeStrategy:
            probe_table = OpenAddressHashTable(101, strategy)
            total_probes = 0
            collisions = 0
            max_probes = 0
            for key in ids:
                _, probes, _ = probe_table.insert(Equipment(key, f"Оборудование {key}", "A-101", "Свободно"))
                total_probes += probes
                if probes > 1:
                    collisions += 1
                if probes > max_probes:
                    max_probes = probes
            successful = 0
            for key in ids:
                _, _, probes = probe_table.search(key)
                successful += probes
            unsuccessful = 0
            for i in range(count):
                _, _, probes = probe_table.search(2000 + i)
                unsuccessful += probes
            chain_table = ChainedHashTable(101)
            for key in ids:
                chain_table.insert(Equipment(key, f"Оборудование {key}", "A-101", "Свободно"))
            longest = 0
            for node in chain_table.buckets:
                length = 0
                current = node
                while current:
                    length += 1
                    current = current.next
                if length > longest:
                    longest = length
            empty = probe_table.data.count(EMPTY)
            print(f"{fill:.2f} | {strategy.value} | {collisions} | "
                  f"{total_probes / count:.2f} | {max_probes} | "
                  f"{successful / count:.2f} | {unsuccessful / count:.2f} | "
                  f"{longest} | {empty}")


if __name__ == "__main__":
    run_demo()
