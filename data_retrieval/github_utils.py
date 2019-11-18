import ujson
import sys
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport
from data_retrieval.readme_file_utils import RetrieveProjectReadmeTask
from urllib.parse import urlparse


class GitHubUtils:
    
    def __init__(self, auth_token):

        self._transport = RequestsHTTPTransport(
            url='https://api.github.com/graphql',
            use_json=True,
            headers={
                'Authorization': 'Bearer ' + auth_token,
                'Accept': 'application/vnd.github.hawkgirl-preview+json',
            }
        )

        self.client = Client(
            transport=self._transport,
            fetch_schema_from_transport=True,
        )

        self.query = gql('''
            query GetGithubInfo($owner: String!, $name: String!) {
                repository(owner: $owner, name: $name) {
                id
                nameWithOwner
                dependencyGraphManifests(first:100) {
                    totalCount
                    pageInfo {
                        hasNextPage
                    }
                    nodes {
                        dependenciesCount
                        filename
                        dependencies {
                            nodes {
                                packageName
                                repository {
                                    id
                                    nameWithOwner
                                }
                            }
                        }
                    }
                }
                repositoryTopics(first:100) {
                  nodes {
                    topic {
                        id
                        name
                    }
                  }
                }
              }
            }
            ''')

        self.ReadmeTask = RetrieveProjectReadmeTask()


    def get_github_info(self, package_name):
        """
        Get's all relevant github info for a single package.
        Collects the following:
        - Direct dependencies as defined in files like Pipfile
        - GitHub topics chosen by repo's owner

        :param package_name: String of form "<OWNER>/<NAME>/"
        :return: dict of relevant info
        """
        owner, name = list(filter(lambda a: a != '', package_name.split('/')))
        params = {
            'owner': owner,
            'name': name
        }

        # Make request to github API
        res = self.client.execute(self.query, variable_values=ujson.dumps(params))

        # Get direct dependencies
        dep_graph_files = res['repository']['dependencyGraphManifests']['nodes']
        nodes = []

        for dep_graph in dep_graph_files:
            for node_obj in dep_graph['dependencies']['nodes']:
                nodes.append({
                    'packageName': node_obj['packageName'],
                    'repository': node_obj['repository']
                })

        # Get repo topics
        topics_obj_list = res['repository']['repositoryTopics']['nodes']
        topics = []

        for topic_obj in topics_obj_list:
            topics.append({
                "name": topic_obj['topic']['name'],
                "id": topic_obj['topic']['id']
            })

        # Get readme if available
        readme_obj = self.ReadmeTask.run(owner, name)

        # Load all data needed
        return {
            'nameWithOwner': res['repository']['nameWithOwner'],
            'directDependencyGraph': {
                'totalCount': len(nodes),
                'nodes': nodes
            },
            'topics': topics,
            'readme': readme_obj
        }


    def within_github_rate_limit(self):
        query = gql('''
            query {
              viewer {
                login
              }
              rateLimit {
                limit
                cost
                remaining
                resetAt
              }
            }
            ''')

        try:
            self.client.execute(query)
            return True
        except:
            exc_type, value, traceback = sys.exc_info()
            if 'rate_limited' in str(value).lower():
                print('RATE LIMITED')
            else:
                print(f'WEIRD ERROR: {str(value)}')
            return False


    def get_user_repo_format(self, url):
        parsed_url = urlparse(url)

        path = parsed_url.path.split('.')[0]  # Remove anything like .git
        split_path = path.split('/')

        if len(split_path) > 2 and len(split_path[1]) > 0 and len(split_path[2]) > 0:
            # Combine user/repo
            cleaned_github = split_path[1] + '/' + split_path[2]
        else:
            cleaned_github = 'NOTFOUND/NOTFOUND'
        return cleaned_github