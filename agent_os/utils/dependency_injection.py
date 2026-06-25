from typing import Any, Callable, Dict, Type

class Container:
    """
    Simple Inversion of Control (IoC) Container for Dependency Injection.
    """
    def __init__(self):
        self._providers: Dict[Type, Callable[[], Any]] = {}
        self._instances: Dict[Type, Any] = {}

    def register_singleton(self, interface: Type, implementation: Any):
        """Register a pre-instantiated singleton."""
        self._instances[interface] = implementation

    def register_factory(self, interface: Type, factory: Callable[[], Any]):
        """Register a factory function for transient instances."""
        self._providers[interface] = factory

    def resolve(self, interface: Type) -> Any:
        """Resolve a dependency."""
        if interface in self._instances:
            return self._instances[interface]
        if interface in self._providers:
            return self._providers[interface]()
        raise KeyError(f"No provider found for {interface}")

container = Container()
