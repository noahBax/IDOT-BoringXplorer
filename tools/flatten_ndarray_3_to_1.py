def flatten_ndarray_3_to_1(array):
    """
    Meant to flatten a black and white 3d image array down to just a black and
    white 2d array. This is done just by dropping the 2th and 3th dimension
    """

    return array.copy()[:, :, 0]