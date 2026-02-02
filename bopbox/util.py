def find_ord_in_memoryview(
    view: memoryview,
    ord: int,
) -> int:
    for i in range(len(view)):
        if view[i] == ord:
            return i

    return -1
