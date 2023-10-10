from pypylon import pylon
import zmq
#from ..elements.adjustable import AdjustableVirtual, AdjustableGetSet, value_property
#from eco.elements.detector import DetectorGet
#from ..epics.adjustable import AdjustablePv, AdjustablePvEnum
#from eco.elements.adj_obj import AdjustableObject, DetectorObject
#from eco.devices_general.utilities import Changer
#from ..aliases import Alias, append_object_to_object

class Camera():
    def __init__(self,):
        pass
class Camera_Attribute_Callable():
    def __init__(self,call):
        self._call = call
    def __call__(self):
        return self._call()

class ZmqPylonServer():
    def __init__(self,):
        try:
            self.camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())
        except Exception as e:
            print(e)
        self.context = None
        self.socket = None
        self.start()

    def get_images_sum(self, n, *args, **kwargs):
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

    def _get_attr(self, attr, *args, obj = None,  **kwargs):
        if object is None:
            obj = self
        print(attr)
        if attr in dir(obj):
            print(attr)
            attr = getattr(obj, attr)
            if callable(attr):
                dat = attr(*args, **kwargs)
            else:
                dat = attr
            return dat

    def _get_doc(self, attr, *args, obj=None, **kwargs):
        ### is one level with get_attr, which means it has to get an object to only an attr
        if obj is None:
            obj = self
        if attr in dir(obj):
            attr = getattr(obj, attr)
            if callable(attr):
                dat = attr.__doc__
            else:
                dat = ""
            return dat

    def _inspect(self, attr, *args, obj=None, **kwargs):
        ### is one level with get_attr, which means it has to get an object to only an attr
        if obj is None:
            print("Object is NONE")
            obj = self
        doc = ""
        is_call = False
        attrs = []
        if attr in dir(obj):
            attr = getattr(obj, attr)
            if callable(attr):
                doc = attr.__doc__
                is_call = True
                attrs = [a for a in attr.__dir__() if not a[:2]=="__"]
        return [doc, is_call, attrs]

    def get_attr(self, attr, *args, **kwargs):
        print(attr)
        obj = self
        if "childpath" in kwargs.keys() and kwargs["childpath"] is not None:
            print(kwargs["childpath"])
            levels = kwargs.pop("childpath").split(".")
            for lvl in levels:
                print(lvl)
                if lvl in obj.__dict__.keys():
                    obj = obj.__dict__[lvl]
                else:
                    obj = getattr(obj, lvl)
        if attr == "_get_doc":
            return self._get_doc(*args, obj=obj, **kwargs)
        if attr == "_inspect":
            return self._inspect(*args, obj=obj, **kwargs)
        else:
            return self._get_attr(attr, *args, obj=obj, **kwargs)

    def stop(self):

        self.camera.Close()
        self.socket.close()
        self.context.term()
        print("stopped")

    def start(self):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind("tcp://*:5555")
        self.camera.Open()
        try:
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
                try:
                    self.socket.send_pyobj(dat)
                except Exception as e:
                    dat = str(e)
                    self.socket.send_pyobj(dat)
        except Exception as e:
            self.stop()
            print(e)


class ZmqPylonClient():
    def __init__(self,):
        self._context = zmq.Context()
        self._socket = self._context.socket(zmq.REQ)
        self._socket.connect("tcp://slab-cons-02:5555")
        self._add_remote_attrs()

    def _add_remote_attrs(self):
        remattrs = self._send("__dir__")
        camremattrs = self._send("__dir__", childpath="camera")
        locattrs = self.__dir__()
        locattrs = locattrs + ["start", "stop", "context", "socket"]
        for a in remattrs:
            if not a in locattrs:
                setattr(self, a, self._rem_func(a))
                doc = self._send("_get_doc", a)
                f = getattr(self, a)
                f.__doc__ = doc
        self.camera = Camera()

        for a in camremattrs:
            if not a in locattrs:
                self._es = {}
                try:
                    doc, is_call, sub_attrs = self._send("_inspect", a, childpath="camera")
                except Exception as e:
                    self._es[a] = e
                    continue

                if len(sub_attrs)>0:
                    self.camera.__dict__[a] = Camera_Attribute_Callable(self._rem_func(a, childpath="camera"))
                    ca = self.camera.__dict__[a]
                    ca.__doc__ = doc
                    for sub_attr in sub_attrs:
                        try:
                            doc, is_call, sub_sub_attrs = self._send("_inspect", sub_attr, childpath=f"camera.{a}")
                        except Exception as e:
                            self._es[f"{a}.{sub_attr}"] = e
                            continue

                        if len(sub_sub_attrs) >0:
                            print(a, sub_attr, "has even more attributes")
                            print(attrs)
                        if is_call:
                            setattr(ca, sub_attr, self._rem_func(sub_attr, childpath=f"camera.{a}"))
                            f = getattr(ca, sub_attr)
                            f.__doc__ = doc
                else:
                    setattr(self.camera, a, self._rem_func(a, childpath="camera"))
                    doc = self._send("_get_doc", a, childpath="camera")
                    f = getattr(self.camera, a)
                    f.__doc__ = doc

    def _send(self, attr, *args, **kwargs):
        self._socket.send_pyobj([attr, args, kwargs])
        dat = self._socket.recv_pyobj()
        return dat

    def _rem_func(self, attr, childpath=None):
        return lambda *args, **kwargs : self._send(attr, childpath=childpath, *args, **kwargs)

#        self._append(AdjustableGetSet, 
#                     self._get_config, 
#                     self._set_config, 
#                     cache_get_seconds =.05, 
#                     precision=0, 
#                     check_interval=None, 
#                     name='_config', 
#                     is_setting=False, 
#                     is_display=False)
#
#        self._append(AdjustableObject, self._config, name='config',is_setting=True, is_display='recursive')
#
#    def _get_config(self):
#        return  self.cc.get_camera_config(self.cam_id)
#
#    def _set_config(self, value, hold=False):
#        return Changer(
#            target=value,
#            changer=lambda v: self.cc.set_camera_config(self.cam_id, v),
#            hold=hold,
#        )
#

#@value_property

