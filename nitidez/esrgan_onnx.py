"""Convierte Real-ESRGAN realesr-general-x4v3 (SRVGGNetCompact) a ONNX sin PyTorch.

Uso: python3 esrgan_onnx.py <x4v3.pth> <wdn-x4v3.pth> <salida.onnx> [fuerza_ruido=0.5]

fuerza_ruido mezcla los pesos como hace Real-ESRGAN (-dn): 1 = modelo normal (más detalle),
0 = modelo "wdn" (más reducción de ruido).
"""
import pickle
import sys
import zipfile
from collections import OrderedDict

import numpy as np
import onnx
from onnx import TensorProto, helper, numpy_helper

DTYPES = {"FloatStorage": np.float32, "HalfStorage": np.float16}


def cargar_pesos(path):
    """Lee un .pth (zip de PyTorch) con un unpickler restringido: solo reconstruye tensores."""
    z = zipfile.ZipFile(path)
    raiz = z.namelist()[0].split("/")[0]

    class Almacen:
        def __init__(self, tipo, clave):
            self.dtype = DTYPES[tipo]
            self.datos = np.frombuffer(z.read(f"{raiz}/data/{clave}"), self.dtype)

    def rebuild(almacen, offset, forma, pasos, *_):
        if not forma:
            return almacen.datos[offset:offset + 1].reshape(()).astype(np.float32)
        return np.lib.stride_tricks.as_strided(
            almacen.datos[offset:], shape=forma,
            strides=[s * almacen.datos.itemsize for s in pasos]).copy().astype(np.float32)

    class Lector(pickle.Unpickler):
        def find_class(self, modulo, nombre):
            if (modulo, nombre) == ("collections", "OrderedDict"):
                return OrderedDict
            if (modulo, nombre) == ("torch._utils", "_rebuild_tensor_v2"):
                return rebuild
            if modulo == "torch" and nombre in DTYPES:
                return nombre
            raise pickle.UnpicklingError(f"global no permitido: {modulo}.{nombre}")

        def persistent_load(self, pid):
            _, tipo, clave, _, _ = pid
            return Almacen(tipo, clave)

    estado = Lector(z.open(f"{raiz}/data.pkl")).load()
    for k in ("params_ema", "params"):
        if isinstance(estado, dict) and k in estado:
            return estado[k]
    return estado


def construir(pesos, salida):
    nodos, inits = [], []
    x = "entrada"
    capas = sorted({int(k.split(".")[1]) for k in pesos}, key=int)
    for idx in capas:
        w = pesos[f"body.{idx}.weight"]
        nombre = f"b{idx}"
        if w.ndim == 4:  # convolución 3x3
            inits += [numpy_helper.from_array(w, f"{nombre}_w"),
                      numpy_helper.from_array(pesos[f"body.{idx}.bias"], f"{nombre}_b")]
            nodos.append(helper.make_node("Conv", [x, f"{nombre}_w", f"{nombre}_b"], [nombre],
                                          pads=[1, 1, 1, 1], kernel_shape=[3, 3]))
        else:  # PReLU por canal
            inits.append(numpy_helper.from_array(w.reshape(-1, 1, 1), f"{nombre}_a"))
            nodos.append(helper.make_node("PRelu", [x, f"{nombre}_a"], [nombre]))
        x = nombre
    # pixel shuffle x4 (equivale a DepthToSpace CRD) + entrada ampliada (vecino más cercano)
    nodos.append(helper.make_node("DepthToSpace", [x], ["ps"], blocksize=4, mode="CRD"))
    inits.append(numpy_helper.from_array(np.array([1, 1, 4, 4], np.float32), "escalas"))
    nodos.append(helper.make_node("Resize", ["entrada", "", "escalas"], ["base"], mode="nearest"))
    nodos.append(helper.make_node("Add", ["ps", "base"], ["salida"]))
    g = helper.make_graph(
        nodos, "srvgg_x4",
        [helper.make_tensor_value_info("entrada", TensorProto.FLOAT, [1, 3, "h", "w"])],
        [helper.make_tensor_value_info("salida", TensorProto.FLOAT, [1, 3, "H", "W"])], inits)
    m = helper.make_model(g, opset_imports=[helper.make_opsetid("", 17)], ir_version=8)
    onnx.checker.check_model(m)
    onnx.save(m, salida)


def main():
    a, b, salida = sys.argv[1:4]
    fuerza = float(sys.argv[4]) if len(sys.argv) > 4 else 0.5
    pa, pb = cargar_pesos(a), cargar_pesos(b)
    pesos = {k: fuerza * pa[k] + (1 - fuerza) * pb[k] for k in pa}
    construir(pesos, salida)
    print(f"ONNX guardado: {salida} ({len(pesos)} tensores, fuerza de ruido {fuerza})")


if __name__ == "__main__":
    main()
