print("\n====================================")
print("   PRUEBA DE PISTOLA LÁSER")
print("   Escanea un producto ahora")
print("   (Escribe SALIR para terminar)")
print("====================================\n")

while True:
    codigo = input("Escanea: ").strip()

    if codigo.upper() == "SALIR":
        print("\nPrueba finalizada.")
        break

    print(f"Leído: [{codigo}]")