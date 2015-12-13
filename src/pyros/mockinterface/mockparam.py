from __future__ import absolute_import, print_function


"""
ParamBack is the class handling conversion from Python API to Mock Param
"""
class MockParam:
    def __init__(self, param_name, param_type):
        self.name = param_name
        # getting the fullname to make sure we start with /
        self.fullname = self.name if self.name.startswith('/') else '/' + self.name

        self.value = param_type()  # or None ??

    def cleanup(self):
        pass

    def set(self, val):
        self.value = val
        return True

    def get(self):
        return self.value
