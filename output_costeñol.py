# -- Codigo generado por Compilador COSTEÑOL -- CUL --

num1 = 0  # Entero
num2 = 0  # Entero
resultado = 0  # Entero
nombre = ""  # Texto
promedio = 0.0  # Real
activo = False  # Logico
contador = 0  # Entero
nombre = input("  Ingrese Texto: ")
num1 = int(input("  Ingrese Entero: "))
num2 = int(input("  Ingrese Entero: "))
resultado = num1 + num2
promedio = resultado / 2
activo = True
print("Resultado de la suma:")
print(resultado)
if resultado > 10:
    print("El resultado es mayor a 10")
else:
    print("El resultado es menor o igual a 10")
contador = 0
while contador < num1:
    print(contador)
    contador = contador + 1