class Address(str): 
    def __new__(cls, value):
        if len(value) > 42:
            raise ValueError("The address you gave is more too long")
        try:
            int(value, 0)
        except ValueError:
            raise ValueError("The address submitted is hill formed")
        return cls.__init__(value)