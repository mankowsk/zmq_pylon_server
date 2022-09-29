from pypylon import pylon
import zmq

class ZmqPylonServer():
    def __init__(self,):
        try:
            self.camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())
        except Exception as e:
            print(e)

        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind("tcp://*:5555")


    def get_images_sum(self, n):
        numberOfImagesToGrab = n
        self.camera.StartGrabbingMax(numberOfImagesToGrab)
        img = None
        while self.camera.IsGrabbing():
            grabResult = self.camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
            if grabResult.GrabSucceeded():
            #print("SizeX: ", grabResult.Width)
                if img is None:
                    img = grabResult.Array
                else:
                    img = img+grabResult.Array
        grabResult.Release()
        return img

    def _get_attr(self, attr, obj, *args, **kwargs):
        if attr in dir(obj):
            attr = getattr(obj, attr)
            if callable(attr):
                dat = attr(*args, **kwargs)
            else:
                dat = attr
            return dat

    def get_attr(self, attr, *args, **kwargs):
        obj = self
        if "childpath" in kwargs.keys():
            levels = kwargs["childpath"].split(".")
            for lvl in levels:
                obj = obj.__dict__[lvl]
        return self._get_attr(attr, obj, *args, **kwargs)

    def start(self):
        while True:
            #  Wait for next request from client
            attr, args, kwargs = self.socket.recv_pyobj()
            print(f"Received request: {[attr, args, kwargs]}")
            dat = ""
            try:
                dat = self.get_attr(attr, *args, **kwargs)
            except Exception as e:
                dat = str(e)
            #  Send reply back to client
            self.socket.send_pyobj(dat)


class ZmqPylonClient():
    def __init__(self,):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect("tcp://slab-cons-02:5555")
        self._add_remote_attrs()
    def _add_remote_attrs(self):
        remattrs = self.send("__dir__")
        locattrs = self.__dir__()
        for a in remattrs:
            if not a in locattrs:
                setattr(self, a, self._rem_func(a))
    def send(self, attr, *args, **kwargs):
        self.socket.send_pyobj([attr, args, kwargs])
        dat = self.socket.recv_pyobj()
        return dat

    def _rem_func(self, attr):
        return lambda *args, **kwargs : self.send(attr, *args, **kwargs)


