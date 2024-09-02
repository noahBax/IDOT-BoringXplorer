from math import ceil, floor


def find_outliers(data: list[float]):
    """
    Find outliers using the 1.5xIQR rule
    https://www.khanacademy.org/math/statistics-probability/summarizing-quantitative-data/box-whisker-plots/a/identifying-outliers-iqr-rule
    """

    # Sort the data if not already sorted
    data.sort()

    q1: float
    q3: float

    size = len(data)
    if size % 2 == 1:
        a = (size - 1) / 2
        q1_index = (a - 1) / 2
        q3_index = size - q1_index - 1
        q1 = (data[floor(q1_index)] + data[ceil(q1_index)]) / 2
        q3 = (data[floor(q3_index)] + data[ceil(q3_index)]) / 2
    else:
        a = size / 2
        q1_index = (a - 1) / 2
        q3_index = size - q1_index - 1
        q1 = (data[floor(q1_index)] + data[ceil(q1_index)]) / 2
        q3 = (data[floor(q3_index)] + data[ceil(q3_index)]) / 2
    print(q1, q3)