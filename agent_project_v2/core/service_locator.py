class ServiceLocator:
    _services = {}

    @classmethod
    def register(cls, service_name, service_instance):
        cls._services[service_name] = service_instance

    @classmethod
    def get(cls, service_name):
        return cls._services.get(service_name)

# import threading
#
# class ServiceLocator:
#     _services = {}
#     _lock = threading.Lock()
#
#     @classmethod
#     def register(cls, name: str, instance):
#         with cls._lock:
#             cls._services[name] = instance
#
#     @classmethod
#     def get(cls, name: str):
#         with cls._lock:
#             service = cls._services.get(name)
#             if service is None:
#                 raise ValueError(f"Service '{name}' not found in ServiceLocator.")
#             return service
