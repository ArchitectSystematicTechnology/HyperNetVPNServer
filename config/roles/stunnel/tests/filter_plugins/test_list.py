def test_list(l):
    """
    Return true if object is a list
    """
    return isinstance(l, list)

class FilterModule(object):
    def filters(self):
        return {
            'is_list' : test_list
        }
