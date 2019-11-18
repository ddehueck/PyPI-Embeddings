from urllib.parse import urlparse
from tqdm import tqdm
import multiprocessing
from multiprocessing.dummy import Pool as ThreadPool
import ujson
import sys
import os
from data_retrieval.github_utils import GitHubUtils


class RetrieveGitHubData:
     
    def __init__(self, save_to, pypi_github_path, auth_token):
        self.save_to = save_to
        self.pypi_github_path = pypi_github_path
        self.utils = GitHubUtils(auth_token)


    def get_all_github_data(self, batch_size=250):
        with open(self.save_to, 'r', encoding='utf-8') as f:
            # The data map stores every package indicating if we have data or if a certain error was raised
            data_map = ujson.loads(f.read())

        with open(self.pypi_github_path, 'r', encoding='utf-8') as f:
            json = ujson.loads(f.read())

        # Ensure we have all the potential github repos
        assert len(json['data']) == len(data_map.keys())

        # Set up list to be batched and distributed to workers
        print('Setting up packages to be distributed to workers...')
        dist_list = []
        for pkg in data_map:
            dist_list.append({
                'name': pkg,
                **data_map[pkg]
            })

        assert len(dist_list) == len(data_map)

        # Load Thread Pool and distributed to workers
        num_exceptions = 0
        pool = ThreadPool(multiprocessing.cpu_count())
        file_batches = self._batch_list(batch_size, dist_list)

        print('Getting all github data...')
        for batch_results, n_exceptions in tqdm(
                pool.imap_unordered(self._get_github_data_worker, file_batches),
                total=len(dist_list) // batch_size + 1):

            # Reduce into larger dict
            data_map.update(batch_results)
            num_exceptions += n_exceptions

        pool.close()
        pool.join()

        # Log and save at completion
        print(f'There were {num_exceptions} exceptions out of {len(data_map)} requests.')
        print(f'Saving data...')

        with open(self.save_to, 'w', encoding='utf-8') as f:
            ujson.dump(data_map, f)

        print(f'Saved data to: {self.save_to}')
        self.print_stats(data_map)


    def _get_github_data_worker(self, batch):
        results = dict()
        n_exceptions = 0

        for pkg_dict in batch:
            try:
                cleaned_url = self.utils.get_user_repo_format(pkg_dict['github_link'])

                # Skip any packages that we are waiting on
                if pkg_dict['error'] or pkg_dict['data'] is not None:
                    continue
                else:
                    pkg_dict['data'] = self.utils.get_github_info(cleaned_url)
                    pkg_dict['error'] = False

            except Exception as e:
                exc_type, value, traceback = sys.exc_info()

                if 'rate_limited' in str(value).lower():
                    pkg_dict['error'] = False
                    print('RATE_LIMITED')
                    break
                elif '403' in str(value).lower():
                    # For wierd 203 client errors
                    pkg_dict['error'] = False
                elif 'not_found' in str(value).lower():
                    # An unchangeable error
                    pkg_dict['error'] = 'NOT_FOUND'
                else:
                    print(f'\nError: {str(value)} \n URL: {pkg_dict["github_link"]}\n')
                    pkg_dict['error'] = True

                n_exceptions += 1

            results[pkg_dict['name']] = dict(
                github_link=pkg_dict['github_link'],
                data=pkg_dict['data'],
                error=pkg_dict['error'],
            )

        return results, n_exceptions


    def init_data_map(self):
        """
        Initializes a state for every package: state is either errored or has data
        """
        
        if os.path.exists(self.save_to):
            raise Exception("The data map has already been initialized! Delete it if you are sure you want to start over.")
            
        with open(self.pypi_github_path, 'r', encoding='utf-8') as f:
            json = ujson.loads(f.read())

        data_map = {}    
        for pkg in json['data']:
            # Dict is: pkg_name --> data
            data_map[pkg['name']] = dict(
                github_link=pkg['github_link'],
                data=None,
                error=None
            )

        with open(self.save_to, 'w', encoding='utf-8') as f:
            ujson.dump(data_map, f)
        
        print(f'Initialized Data Map to: {self.save_to}')


    def _batch_list(self, batch_size, list_to_batch):
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
            yield list_to_batch[b_idx:min(b_idx + batch_size, n)]


    def print_stats(self, dm):
        d, e = 0, 0
        for pkg in dm:
            if dm[pkg]['data'] is not None:
                d += 1
            if dm[pkg]['error']:
                e += 1

        print('\n------------- SOME STATS -------------------')
        print(f'There were {d} packages with data')
        print(f'There were {e} packages that throw errors')
        print(f'There are {len(dm)} packages total')
        print('--------------------------------------------\n\n')


    def clear_error(self):
        print('CLEARING ERRORS...')
        with open(self.save_to, 'r', encoding='utf-8') as f:
            # The data map stores every package indicating if we have data or if a certain error was raised
            dm = ujson.loads(f.read())

        for pkg in dm:
            # Only clear errors that are changeable - loading error/weird 403s
            # Only 404 not found is viewed as unchangeable - up to user when to terminate
            if dm[pkg]['error'] != 'NOT_FOUND':
                dm[pkg]['error'] = False

                # Log and save at completion
        print(f'Saving data to /data...')

        with open(self.save_to, 'w', encoding='utf-8') as f:
            ujson.dump(dm, f)

        print(f'Saved data to: {self.save_to}')
        self.print_stats(dm)

