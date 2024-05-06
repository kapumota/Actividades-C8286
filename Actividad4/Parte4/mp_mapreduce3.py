from collections import defaultdict
import multiprocessing as mp
import sys
import time
from time import sleep

def report_progress(map_returns, tag, callback):
    done = 0
    num_jobs = len(map_returns)
    while num_jobs > done:
        done = 0
        for ret in map_returns:
            if ret.ready():
                done += 1
        sleep(0.5)
        if callback:
            callback(tag, done, num_jobs - done)


def chunk0(my_list, chunk_size):
    for i in range(0, len(my_list), chunk_size):   #requires a list
        yield my_list[i:i + chunk_size]


def chunk(my_iter, chunk_size):
    chunk_list = []
    for elem in my_iter:
        chunk_list.append(elem)
        if len(chunk_list) == chunk_size:
            yield chunk_list
            chunk_list = []
    if len(chunk_list) > 0:
        yield chunk_list


def chunk_runner(fun, data):
    ret = []
    for datum in data:
        ret.append(fun(datum))
    return ret

def chunked_async_map(pool, mapper, data, chunk_size):
    async_returns = []
    for data_part in chunk(data, chunk_size):
        async_returns.append(pool.apply_async(
            chunk_runner, (mapper, data_part)))  
    return async_returns


def map_reduce(pool, my_input, mapper, reducer, chunk_size, callback=None): 
    map_returns = chunked_async_map(pool, mapper, my_input, chunk_size)
    report_progress(map_returns, 'map', callback)
    map_results = []
    for ret in map_returns:
        map_results.extend(ret.get()) 
    distributor = defaultdict(list)
    for key, value in map_results:
        distributor[key].append(value)
    returns = chunked_async_map(pool, reducer, distributor.items(), chunk_size)
    report_progress(returns, 'reduce', callback)
    results = []
    for ret in returns:
        results.extend(ret.get())
    return results


def emitter(word):
    return word, 1


def counter(emitted):
    return emitted[0], sum(emitted[1])


def reporter(tag, done, not_done):
    print(f'Operacion {tag}: {done}/{done+not_done}')

def run_map_reduce(words, chunk_size):
    pool = mp.Pool()
    start_time = time.time()
    counts = map_reduce(pool, words, emitter, counter, chunk_size, reporter)
    pool.close()
    pool.join()
    end_time = time.time()
    duration = end_time - start_time
    return duration


if __name__ == '__main__':
    words = [word
             for word in map(lambda x: x.strip().rstrip(),
                             ' '.join(open('texto.txt', 'rt', encoding='utf-8').readlines()).split(' '))
             if word != '' ]

    chunk_sizes = [1, 10, 100, 1000, 10000]
    results = []

    for size in chunk_sizes:
        duration = run_map_reduce(words, size)
        results.append((size, duration))

    print("Tam fragmentacion | Duracion")
    print("-" * 20)
    for size, duration in results:
        print(f"{size:<10} | {duration:.2f} segundos")
