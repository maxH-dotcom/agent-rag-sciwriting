import time
from typing import Literal
import datetime
import httpx
import pydantic


class BaseModel(pydantic.BaseModel):
    class Config:
        extra = "allow"

    def to_dict(self):
        return self.model_dump()

    def to_json(self):
        return self.model_dump_json()


class Author(BaseModel):
    display_name: str
    id: str

    # Be ok with extra fields
    class Config:
        extra = "allow"

    def last_first(self):
        names = self.display_name.split()
        return f"{names[-1]}, {' '.join(names[:-1])}"


class Authorship(BaseModel):
    author: Author

    # Be ok with extra fields
    class Config:
        extra = "allow"

    @pydantic.validator("author", pre=True)
    def author_to_object(cls, author):
        return Author(**author) if isinstance(author, dict) else author


class Source(BaseModel):
    id: str
    display_name: str

    # Be ok with extra fields
    class Config:
        extra = "allow"


class Location(BaseModel):
    is_oa: bool
    source: Source

    @pydantic.validator("source", pre=True)
    def source_to_object(cls, source):
        return Source(**source) if isinstance(source, dict) else source

    # Be ok with extra fields
    class Config:
        extra = "allow"


class Work(BaseModel):
    id: str
    title: str
    authorships: list[Authorship]
    publication_date: datetime.date
    locations: list[Location]

    # To make the class generate Authorship objects
    @pydantic.validator("authorships", pre=True)
    def authorships_to_objects(cls, authorships):
        return [
            Authorship(**authorship) if isinstance(authorship, dict) else authorship
            for authorship in authorships
        ]

    @pydantic.validator("publication_date", pre=True)
    def publication_date_to_object(cls, publication_date):
        return datetime.datetime.strptime(publication_date, "%Y-%m-%d").date()

    @pydantic.validator("locations", pre=True)
    def locations_to_objects(cls, locations):
        return [
            Location(**location) if isinstance(location, dict) else location
            for location in locations
            if location and location.get("source")
        ]

    # Be ok with extra fields
    class Config:
        extra = "allow"

    def simple_id(self):
        """
        Return a first-author-lastname-title-year string for the work.
        For example, "MatelskyDotMotif2021".
        """
        first_author = self.authorships[0].author.last_first().split(",")[0]
        year = self.publication_date.year
        title_words = "".join(
            [c for c in self.title if c.isalpha() or c.isspace()]
        ).split()
        return f"{first_author}{title_words[0]}{year}"

    def to_bibtex(self):
        authors = " and ".join(
            [author.author.display_name for author in self.authorships]
        )
        return f"""
@article{{{self.simple_id()},
    author = {{{authors}}},
    title = {{{self.title}}},
    year = {{{self.publication_date.year}}},
    journal = {{{self.locations[0].source.display_name}}},
}}
"""

    def to_mla(self):
        # If there are three or more authors, list only the first author followed by the phrase et al.
        # If there are two, list "and" between the names (Last, First and First Last)
        # If there is only one author, list the author's name normally (Last, First)
        if len(self.authorships) > 2:
            authors = self.authorships[0].author.last_first() + ", et al"
        elif len(self.authorships) == 2:
            authors = (
                self.authorships[0].author.last_first()
                + " and "
                + self.authorships[1].author.last_first().split(",")[1]
                + " "
                + self.authorships[1].author.last_first().split(",")[::-1][0]
            )
        else:
            authors = self.authorships[0].author.last_first()
        return f'{authors}. "{self.title}." {self.locations[0].source.display_name}, {self.publication_date.year}.'


def sluggable(func):
    """
    A decorator that adds an extra option to the function to return the slug.

    Argumentss:
        func (callable): The function to be decorated.

    Returns:
        callable: The decorated function.

    Example:
        @sluggable
        def my_function():
            # function implementation
            pass

        result = my_function(return_slug=True)
        # returns the slug of the response

    """

    def wrapper(*args, **kwargs):
        return_slug = kwargs.pop("return_slug", False)
        response = func(*args, **kwargs)
        if return_slug:
            return OpenAlex.get_slug_from_uri(response)
        return response

    return wrapper


def depaginated(func):
    """
    A decorator that handles pagination for OpenAlex API requests.

    Arguments:
        func (callable): The function to be decorated.

    Returns:
        callable: The decorated function.

    """

    # Automatically handle pagination. Meta looks like this in each req:
    #     {'meta': {'count': 48,
    # 'db_response_time_ms': 24,
    # 'page': 1,
    # 'per_page': 25,
    # 'groups_count': None},
    # 'results': [{'id': 'https://openalex.org/works/1', ...
    def wrapper(*args, **kwargs):
        response = func(*args, **kwargs)
        results = response["results"]
        page = 1
        while len(results) < response["meta"]["count"]:
            page += 1
            response = func(*args, **kwargs, page=page)
            results.extend(response["results"])
        return results

    return wrapper


class OpenAlex:
    """
    A class for interacting with the OpenAlex API.

    Args:
        mailto (str): The email address to use in requests to keep you in the nice pool.
        base_url (str, optional): The base URL of the OpenAlex API. Defaults to "https://api.openalex.org/".

    Attributes:
        base_url (str): The base URL of the OpenAlex API.
        client (httpx.Client): An HTTP client for making requests to the API.

    """

    def __init__(self, mailto: str, **kwargs):
        """
        Initializes a new instance of the class.

        Args:
            base_url (str, optional): The base URL for the API. Defaults to "https://api.openalex.org/".

        """
        self.mailto = mailto
        self.base_url = kwargs.get("base_url", "https://api.openalex.org/")
        self.client = httpx.Client()

    def _get(self, endpoint, retry_429: bool | int = 5, **kwargs):
        url = self.base_url + endpoint
        response = self.client.get(url, **kwargs)
        if response.status_code == 429 and retry_429:
            time.sleep(1)
            return self._get(endpoint, retry_429 - 1, **kwargs)
        response.raise_for_status()
        return response.json()

    def _get_noun(self, noun: Literal["works", "authors"], **kwargs):
        filter_params = kwargs.get("filter", {})
        filter_string = (
            "filter=" + ",".join([f"{k}:{v}" for k, v in filter_params.items()])
            if filter_params
            else ""
        )
        page = kwargs.get("page", 1)
        if self.mailto:
            return self._get(f"{noun}?{filter_string}&page={page}&mailto={self.mailto}")
        return self._get(f"{noun}?{filter_string}&page={page}")

    @depaginated
    def get_works(self, **kwargs):
        return self._get_noun("works", **kwargs)

    @depaginated
    def get_authors(self, **kwargs):
        return self._get_noun("authors", **kwargs)

    @depaginated
    def get_citers(self, work_slug: str, **kwargs):
        page = kwargs.get("page", 1)
        if self.mailto:
            return self._get(
                f"works?filter=cites:{work_slug}&page={page}&mailto={self.mailto}"
            )
        return self._get(f"works?filter=cites:{work_slug}&page={page}")

    @sluggable
    def get_author_uri_by_search(self, search: str):
        if self.mailto:
            response_data = self._get(f"authors?search={search}&mailto={self.mailto}")
        else:
            response_data = self._get(f"authors?search={search}")
        if "results" in response_data:
            return response_data["results"][0]["id"]
        else:
            raise ValueError("No results found for search " + search)

    @sluggable
    def get_author_uri_by_orcid(self, search: str):
        if self.mailto:
            response_data = self._get(f"authors/orcid:{search}&mailto={self.mailto}")
        else:
            response_data = self._get(f"authors/orcid:{search}")
        if "id" in response_data:
            return response_data["id"]
        else:
            raise ValueError("No results found for search " + search)

    @sluggable
    def get_work_by_search(self, search: str) -> Work:
        if self.mailto:
            response_data = self._get(f"works?search={search}&mailto={self.mailto}")
        else:
            response_data = self._get(f"works?search={search}")
        if "results" in response_data:
            return Work(**response_data["results"][0])
        else:
            raise ValueError("No results found for search " + search)

    @staticmethod
    def get_slug_from_uri(uri: str):
        return uri.split("/")[-1]

    def get_author_institutions(self, author_id: str):
        if self.mailto:
            response = self._get(f"people/{author_id}?mailto={self.mailto}")
        else:
            response = self._get(f"people/{author_id}")
        return response.get("affiliations")


def slug_from_url(url):
    return url.split("/")[-1]
