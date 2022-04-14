from enum import Enum, EnumMeta
from abc import ABC


class ByteEnum(Enum, ABC):
    """
    An abstract enum class.
    Elements of this enum must be able to be serialized.
    """
    def int(self) -> int:
        return int(self)

    def bytes(self) -> bytes:
        return bytes([self.int()])

    def __int__(self):
        return int(self.value)

    @staticmethod
    def from_bytes(data: bytes, enum: EnumMeta):
        data = int(data[0])
        for v in enum:
            if v.int() == data:
                return v
        return None


class ERequest(ByteEnum):
    """
    An enum class to represent requests.
    """
    NONE = 0
    """An empty enum instance."""

    CAMERA = 0x01
    """A flag for requests from camera clients."""
    DISPLAY = 0x02
    """A flag for requests from display clients."""
    ANY = CAMERA.int() | DISPLAY.int()
    """A flag for requests from any clients."""

    CAMERA_TAKE_PICTURE = CAMERA.int() | 0x10
    """Request to make camera to take a picture."""
    CAMERA_TOGGLE_TORCH = CAMERA.int() | 0x20
    """Request to make camera to turn on/off the flashlight."""

    DISPLAY_TAKE_PICTURE = DISPLAY.int() | 0x10
    """Request to make display to take a picture."""
    DISPLAY_SHOW_PICTURE = DISPLAY.int() | 0x20
    """Request to make display to display an image."""

    ANY_QUIT = ANY.int() | 0x10
    """Request to terminate connection."""

    def is_for(self, request):
        value = request.int()
        return (self.int() & value) == value

    def is_for_camera(self):
        return self.is_for(ERequest.CAMERA)

    def is_for_display(self):
        return self.is_for(ERequest.DISPLAY)

    def is_for_any(self):
        return self.is_for(ERequest.ANY)

    @staticmethod
    def from_bytes(data: bytes, enum: EnumMeta = None):
        return ByteEnum.from_bytes(data, ERequest)


class EResponse(ByteEnum):
    """
    An enum class to represent responses.
    """
    NONE = 0
    """An empty enum instance."""
    OK = 1
    """Is sent when operation for the request is normally done."""
    ACK = 2
    """Is sent to let the requestor know that the request is accepted."""
    REJECT = 3
    """Is sent when the receiver rejected the request."""
    ERROR = 4
    """Is sent when some error occurred while working on the requst."""

    @staticmethod
    def from_bytes(data: bytes, enum: EnumMeta = None):
        return ByteEnum.from_bytes(data, EResponse)
