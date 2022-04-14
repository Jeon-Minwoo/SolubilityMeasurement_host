from byte_enum import ERequest, EResponse


class Bundle:
    """
    A bundle for interaction with clients.
    """
    def __init__(self,
                 request_id: int,
                 request: ERequest,
                 args: bytes = b'',
                 response: EResponse = EResponse.NONE):
        self.request_id = request_id
        self.request = request
        self.args = args
        self.response = response

    def bytes(self):
        """
        :return: Serialize this bundle into byte array.
        """
        return self.__bytes__()

    def __bytes__(self):
        """
        :return: Serialize this bundle into byte array.
        """
        return b''.join([
            bytes(self.request_id),
            self.request.bytes(),
            self.response.bytes(),
            self.args])

    def __iter__(self):
        return iter([self.request_id, self.request, self.args, self.response])

    @staticmethod
    def from_bytes(data: bytes):
        """
        Deserialize a byte array into a bundle instance.
        :param data:
        :return:
        """
        return Bundle(
            data[0],
            ERequest.from_bytes(data[1:2]),
            args=data[3:],
            response=EResponse.from_bytes(data[2:3])
        )
