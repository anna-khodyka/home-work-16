# pylint: disable=W0703
# pylint: disable=C0103
"""
LRU cache implementation on Redis
Invalidation and flush cache  function also present

"""

from inspect import signature
import pickle
import redis


r = redis.Redis(
    host="localhost",
    port=6379,
)


def flush_cache():
    """
    clear all entities in redis
    :return: none
    """
    try:
        r.flushdb()
    except Exception as e:
        with open("LRU log.txt", "a", encoding="utf-8") as log:
            log.write("Impossible to flush cache\n")
            log.write(f"There is a problem with LRU cache system: {e}\n")


def LRU_cache(max_len):
    """
    Caching functions results for max_len last recently used *args, **kwargs
    Powered by redis
    :param max_len: int
    :return: res
    """

    def wrapper(func_to_cache):
        def get_args(*args, **kwargs):
            param_dict = {}
            sig = signature(func_to_cache)
            bnd = sig.bind(*args, **kwargs)
            for param in sig.parameters.keys():
                if param in bnd.arguments:
                    param_dict[param] = bnd.arguments[param]
                else:
                    param_dict[param] = sig.parameters[param].default
            lru_cache = func_to_cache.__name__
            try:
                hash_ = str(param_dict).encode()
                members = r.lrange(lru_cache, 0, -1)
                if hash_ not in members:
                    res = func_to_cache(*args, **kwargs)
                    if len(members) < max_len:
                        r.lpush(lru_cache, hash_)
                    else:
                        hash_to_del = r.rpop(lru_cache)
                        r.delete(pickle.dumps((hash_to_del, lru_cache)))
                        r.lpush(lru_cache, hash_)
                    r.set(pickle.dumps((hash_, lru_cache)), pickle.dumps(res))
                    return res
                if len(members) < max_len:
                    r.lrem(lru_cache, 0, hash_)
                    r.lpush(lru_cache, hash_)
                return pickle.loads(r.get(pickle.dumps((hash_, lru_cache))))
            except Exception as error:
                with open("LRU log.txt", "a", encoding="utf-8") as log:
                    log.write(
                        f"Impossible to cache value for function{func_to_cache}\n"
                    )
                    log.write(f"There is a problem with LRU cache system: {error}\n")
                    log.write(f"Function value: {func_to_cache(*args, **kwargs)}\n")
                return func_to_cache(*args, **kwargs)

        return get_args

    return wrapper


def LRU_cache_invalidate(*function_names):
    """
    clear cache in case changes of initial entities (DB update, insert, delete operation)
    :param function_names: str
    :return: None
    """

    def wrapper(func_to_invalidate):
        def get_args(*args, **kwargs):
            res = func_to_invalidate(*args, **kwargs)
            try:
                for function in function_names:
                    param_hashes = r.lrange(function, 0, -1)
                    if param_hashes:
                        for hash_ in param_hashes:
                            r.delete(pickle.dumps((hash_, function)))
                        r.ltrim(function, -1, -1)
                        r.lpop(function)
            except Exception as error:
                with open("LRU log.txt", "a", encoding="utf-8") as log:
                    log.write(
                        f"Impossible to invalidate cache for function{function_names}\n"
                    )
                    log.write(f"There is a problem with LRU cache system: {error}\n")
            return res

        return get_args

    return wrapper
