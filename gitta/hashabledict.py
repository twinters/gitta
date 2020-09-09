class hashabledict(dict):
    """ From https://stackoverflow.com/questions/1151658/python-hashable-dicts """

    def __key(self):
        return tuple((k, self[k]) for k in sorted(self))

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        return self.__key() == other.__key()
