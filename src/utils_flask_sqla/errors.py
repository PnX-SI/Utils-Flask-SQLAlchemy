class UtilsSqlaError(Exception):
    def __init__(self, message, status_code=500):
        Exception.__init__(self)
        self.message = message
        self.status_code = status_code
        raised_error = self.__class__.__name__
        log_message = "Raise: {}, {}".format(
            raised_error,
            message
        )

    def to_dict(self):
        return {
            'message': self.message,
            'status_code': self.status_code,
            'raisedError': self.__class__.__name__
        }

    def __str__(self):
        message = "Error {}, Message: {}, raised error: {}"
        return message.format(
            self.status_code,
            self.message,
            self.__class__.__name__
        )
