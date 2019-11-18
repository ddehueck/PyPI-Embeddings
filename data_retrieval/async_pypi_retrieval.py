import requests
from tqdm import tqdm
from thoth.python import Source
import multiprocessing
from multiprocessing.dummy import Pool as ThreadPool
import ujson
import time


PYPI = Source(url="https://pypi.org/simple")
all_packages = list(PYPI.get_packages())[:100] # Remove limitttt
api_url = PYPI.get_api_url()

print(f'Scanning {len(all_packages)} packages')


def get_all_packages(save_to, batch_size=1000):

    num_exceptions = 0
    collected_data = []

    pool = ThreadPool(multiprocessing.cpu_count())
    file_batches = _batch_list(batch_size, all_packages)

    print('Getting all packages...')
    for batch_results, n_exceptions in tqdm(
            pool.imap_unordered(_get_packages_worker, file_batches),
            total=len(all_packages) // batch_size + 1):

        # Add to global list
        collected_data.extend(batch_results)
        num_exceptions += n_exceptions

    pool.close()
    pool.join()

    # Log and save at completion
    print(f'There were {num_exceptions} exceptions out of {len(all_packages)} requests.')
    print(f'Saving data to /data...')

    with open(save_to, 'w', encoding='utf-8') as f:
        ujson.dump({
            "data": collected_data,
            "timestamp": time.time(),
            "pypi_api_url": api_url + "/<PACKAGE_NAME>/json",
        }, f)

    print(f'Saved data to: {save_to}')


def _get_packages_worker(package_batch):
    results = []
    n_exceptions = 0
    
    for package_name in package_batch:
        try:
            response = requests.get(api_url + f"/{package_name}/json")
            response.raise_for_status()

            info = response.json().get('info')

            results.append({
                "name": package_name,
                "description": info.get('description'),
                "project_urls": info.get('project_urls'),
                "author": info.get('author'),
                "classifiers": info.get('classifiers'),
                "license": info.get('license'),
                "summary": info.get('summary'),
                "pypi_url": info.get('package_url'),
            })

        except Exception as e:
            print(e)
            n_exceptions += 1
    return results, n_exceptions


def _batch_list(batch_size, list_to_batch):
    """
    Batch List
    Seperates list into smaller batches of its elements of
    size batch_size
    :param batch_size: Int - size of each batch
    :param list_to_batch: List - what to create batches of
    :returns: Generator of batches
    """
    n = len(list_to_batch)
    for b_idx in range(0, n, batch_size):
        # min() so we don't index outside of self.files
        yield list_to_batch[b_idx:min(b_idx + batch_size, n)]
