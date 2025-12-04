import pkgutil
import importlib
import inspect
from src.songs.song_base import BaseSong
import src.songs.chart_files as chart_package # Importamos la carpeta de canciones

def get_all_songs():
    """
    Escanea la carpeta 'chart_files' y devuelve un diccionario:
    { "Nombre Cancion": InstanciaDeLaCancion }
    """
    songs = {}
    
    # Rutas para buscar módulos
    path = chart_package.__path__
    prefix = chart_package.__name__ + "."

    # Iterar sobre archivos .py en chart_files/
    for _, name, _ in pkgutil.iter_modules(path, prefix):
        try:
            module = importlib.import_module(name)
            
            # Buscar clases dentro del archivo
            for member_name, obj in inspect.getmembers(module):
                # Verificar si es una clase, si hereda de BaseSong y no es BaseSong en sí misma
                if (inspect.isclass(obj) and 
                    issubclass(obj, BaseSong) and 
                    obj is not BaseSong):
                    
                    # Instanciamos la canción
                    song_instance = obj()
                    songs[song_instance.name] = song_instance
        except Exception as e:
            print(f"❌ Error cargando {name}: {e}")
            
    return songs