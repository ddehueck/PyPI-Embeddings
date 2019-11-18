import ujson
from collections import Counter


class GitHub:

    def __init__(self, data_path):

        with open(data_path, 'r', encoding='utf-8') as f:
            self.saved_data = ujson.load(f)

    def get_pkg_dependency_dict(self):
        pkg_dep_dict = {}
        for pkg, data in self.pkgs_with_deps_gen():
            nodes = data['directDependencyGraph']['nodes']
            pkg_dep_dict[pkg] = list(set([n['packageName'] for n in nodes]))
        return pkg_dep_dict

    def pkgs_with_data_gen(self):
        for pkg in self.saved_data:
            if self.saved_data[pkg]['data'] is not None:
                yield pkg, self.saved_data[pkg]['data']

    def pkgs_with_deps_gen(self):
        for pkg, data in self.pkgs_with_data_gen():
            if int(data['directDependencyGraph']['totalCount']) > 0:
                yield pkg, data

    def pkgs_with_topics_gen(self):
        for pkg, data in self.pkgs_with_data_gen():
            if len(data['topics']) > 0:
                yield pkg, data

    def get_readme(self, pkg):
        """
        Get readme data from a package
        :param pkg: Name of a package
        :return: String of README or '' if no data
        """
        if self.saved_data.get(pkg) is None:
            # No pkg found for this package
            return ''
        if self.saved_data[pkg]['data'] is None:
            # No GitHub data for this package
            return ''

        return self.saved_data[pkg]['data']['readme']['content'] or ''

    def get_all_topics(self):
        topics = []
        for pkg, data in self.pkgs_with_topics_gen():
            for t in data['topics']:
                topics.append(t['name'])
        return topics

    def get_evaluation_topics(self, n_top=200):
        """
        Get topics to use in evaluation task

        :param n_top: How many of the most popular topics to return?
        :return: list of topics
        """
        blacklist = ['python', 'python3', 'python-3', 'python-library', 'pypi', 'python2', 'python36', 'python37', 'python27', 'python-2', 'python-package']
        all_topics = self.get_all_topics()

        print(f'Total of {len(set(all_topics))} topics to chose from')
        c = Counter(all_topics)

        print(f'Getting top {n_top} topics')
        topics = [t[0] for t in c.most_common(n_top + len(blacklist))]

        for tag in blacklist:
            if tag in topics:
                topics.remove(tag)
        return topics

    def print_statistics(self):
        print('------------------------------')
        print('    GitHub Data Statistics    ')
        print('------------------------------')

        # How many packages there are
        num_packages = len(self.saved_data)
        print(f"Total Number of GitHub Packages: {num_packages}")

        d, dg, dgr, dgrt = 0, 0, 0, 0
        for pkg in self.saved_data:
            data = self.saved_data[pkg]['data']
            if data is not None:
                d += 1
                if int(data['directDependencyGraph']['totalCount']) > 0:
                    dg += 1
                    if data['readme']['content'] != '':
                        dgr += 1
                        if len(data['topics']) > 0:
                            dgrt += 1

        print(f'There are {d} packages with data')
        print(f'There are {dg} packages with dependency graph data')
        print(f'There are {dgr} packages with README data as well - Can train jointly')
        print(f'There are {dgrt} packages with all needed data: Graph, READMEs, and Topics - Evaluation\n')

        topics = self.get_evaluation_topics()
        reps, total = 0, 0
        for pkg, data in self.pkgs_with_topics_gen():
            for t in data['topics']:
                if t['name'] in topics:
                    reps += 1
                    break
            total += 1

        print(f'Evaluation topics represent {reps}/{total} OR {100 * reps/total}% of packages with topics\n')
