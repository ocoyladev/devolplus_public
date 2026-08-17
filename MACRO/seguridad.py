import os
import getpass
import hashlib
import datetime
import socket
import threading

# El salt de licenciamiento se lee del entorno; el valor por defecto es de
# demostración y no protege nada (ver README, sección "Modo demo").
SALT_SECRETO = os.environ.get("DEVOL_LICENSE_SALT", "demo-license-salt")
LICENCIA_FILE = "licencia.key"

def _obtener_usuario():
    try:
        return os.getlogin()
    except Exception:
        return getpass.getuser()

def _calcular_hash_esperado(usuario):
    """Calcula el hash esperado basado en usuario y salt."""
    usuario = usuario.strip().lower()
    data = f"{usuario}|{SALT_SECRETO}"
    sha256 = hashlib.sha256(data.encode()).hexdigest()
    return sha256[:12].upper()

def validar_acceso():
    """
    DEPRECATED: Usar validar_acceso_gui() para interfaz gráfica.
    Valida la licencia del usuario via archivo local o ingreso manual.
    """
    usuario = _obtener_usuario()
    hash_esperado = _calcular_hash_esperado(usuario)
    
    print(f"Usuario detectado: {usuario}")
    
    # Intentamos ubicar licencia.key en el directorio actual de trabajo
    ruta_licencia = LICENCIA_FILE 

    # 1. Verificar si existe archivo
    if os.path.exists(ruta_licencia):
        try:
            with open(ruta_licencia, "r") as f:
                contenido = f.read().strip()
            
            if contenido == hash_esperado:
                print("Licencia válida encontrada.")
                return True
        except Exception:
            pass # Error leyendo, pediremos clave
            
    # 2. Si no existe o no coincide
    print("-" * 50)
    print("LICENCIA NO ENCONTRADA O INVÁLIDA")
    print("Este aplicativo requiere una licencia activa para su funcionamiento.")
    print(f"ID de Usuario: {usuario}")
    print("Contacte al administrador para obtener su clave de acceso.")
    print("-" * 50)
    
    entrada = input("Ingrese su clave de licencia: ").strip().upper()
    
    if entrada == hash_esperado:
        try:
            # Guardar la clave correcta
            with open(ruta_licencia, "w") as f:
                f.write(hash_esperado)
            
            # Intentar ocultar el archivo en Windows
            try:
                os.system(f"attrib +h {ruta_licencia}")
            except:
                pass
                
            print("Licencia registrada y guardada exitosamente.")
            return True
        except Exception as e:
            print(f"Advertencia: Clave correcta pero no se pudo guardar el archivo ({e})")
            return True
    else:
        print("Clave incorrecta.")
        return False

def verificar_licencia_existente():
    """
    Verifica si existe una licencia válida.
    Retorna: (bool, str, str) -> (valida, usuario, mensaje)
    """
    usuario = _obtener_usuario()
    hash_esperado = _calcular_hash_esperado(usuario)
    ruta_licencia = LICENCIA_FILE
    
    if os.path.exists(ruta_licencia):
        try:
            with open(ruta_licencia, "r") as f:
                contenido = f.read().strip()
            
            if contenido == hash_esperado:
                return True, usuario, "Licencia válida encontrada."
        except Exception:
            pass
    
    return False, usuario, "Licencia no encontrada o inválida."

def guardar_licencia(clave_ingresada):
    """
    Valida y guarda la licencia ingresada.
    Retorna: (bool, str) -> (exito, mensaje)
    """
    usuario = _obtener_usuario()
    hash_esperado = _calcular_hash_esperado(usuario)
    ruta_licencia = LICENCIA_FILE
    
    if clave_ingresada.strip().upper() == hash_esperado:
        try:
            with open(ruta_licencia, "w") as f:
                f.write(hash_esperado)
            
            # Intentar ocultar el archivo en Windows
            try:
                os.system(f"attrib +h {ruta_licencia}")
            except:
                pass
            
            return True, "Licencia registrada y guardada exitosamente."
        except Exception as e:
            return True, f"Clave correcta pero no se pudo guardar el archivo: {e}"
    else:
        return False, "Clave incorrecta. Contacte al administrador para obtener su licencia."

def registrar_log_email(accion, dato_clave=""):
    """
    Envía un log por correo usando Outlook local de forma asíncrona.
    """
    def _enviar_email():
        # Imports diferidos: COM/Outlook solo existe en Windows con Office.
        import win32com.client
        import pythoncom

        # Inicializar COM en este thread (necesario para win32com en threads separados)
        pythoncom.CoInitialize()
        try:
            usuario = _obtener_usuario()
            hostname = socket.gethostname()
            fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Asunto Estandarizado: [LOG DEVOL+] | USUARIO | ACCION
            asunto = f"[LOG DEVOL+] | {usuario} | {accion}"

            cuerpo = f"""
            Reporte Automatizado
            --------------------
            Usuario: {usuario}
            Equipo: {hostname}
            Fecha: {fecha}
            Accion: {accion}
            DatoClave: {dato_clave}
            <FIN_DATOS>
            --------------------
            """
            
            try:
                # Conectar con Outlook
                outlook = win32com.client.Dispatch("Outlook.Application")
                mail = outlook.CreateItem(0) # 0 = olMailItem
                
                mail.To = os.environ.get("DEVOL_LOG_EMAIL", "admin@example.org")
                mail.Subject = asunto
                mail.Body = cuerpo
                
                # Enviar
                mail.Send()
                print(f"[INFO] Email de log enviado exitosamente: {accion}")
                
            except Exception as e:
                print(f"[WARN] No se pudo enviar el reporte por correo: {e}")
        finally:
            # Liberar COM al finalizar el thread
            pythoncom.CoUninitialize()
    
    # Ejecutar en thread separado para no bloquear la ejecución
    thread = threading.Thread(target=_enviar_email, daemon=True)
    thread.start()
