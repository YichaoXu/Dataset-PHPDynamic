# GitHub API Reference

This document summarizes all GitHub API endpoints used in the PHPIncludes project, including request formats, purposes, rate limits, and response handling.

## Overview

The project uses the GitHub REST API v3 to search for PHP repositories, analyze code, and retrieve file contents. All requests are authenticated and include rate limiting and caching mechanisms.

**Base URL**: `https://api.github.com`

## Authentication

All API requests use personal access tokens for authentication:
- **Header**: `Authorization: token <GITHUB_TOKEN>`
- **Environment Variable**: `GITHUB_TOKEN`
- **Configuration File**: `config/config.yml` → `github.api_token`

## API Endpoints

### 1. Code Search API

**Endpoint**: `GET /search/code`

**Purpose**: Search for code snippets across GitHub repositories. Used as the primary method to discover PHP repositories containing specific code patterns (dynamic includes, function calls, etc.).

**Note**: The Code Search API supports two search scopes:
1. **Global Search** (primary usage): Search across all public repositories
2. **Repository-Scoped Search**: Search within a specific repository

The project primarily uses **global search** to discover repositories, not repository-scoped search.

#### 1.1 Global Code Search

**Method**: `search_code_content()`

**Purpose**: Search for code patterns across all public repositories on GitHub to discover relevant repositories.

**Request Format**:
```http
GET https://api.github.com/search/code
Authorization: token <GITHUB_TOKEN>
```

**Query Parameters**:
- `q` (string, required): Search query with qualifiers
  - Format: `{query} language:{language}` (no `repo:` qualifier)
  - Example: `call_user_func language:PHP`
  - Supports OR queries: `call_user_func OR call_user_func_array language:PHP`
  - **Note**: This searches across ALL repositories, not limited to a specific one
- `per_page` (integer, optional): Results per page (max 100, default 30)
- `sort` (string, optional): Sort order (`indexed`, `best-match`)
- `order` (string, optional): Sort direction (`asc`, `desc`)

**Example Request**:
```python
url = "https://api.github.com/search/code"
params = {
    "q": "call_user_func language:PHP",  # Global search, no repo: qualifier
    "per_page": 100,
    "sort": "indexed",
    "order": "desc"
}
```

**Key Points**:
- **No `repo:` qualifier** - searches across all repositories
- Returns results from multiple different repositories
- Used to **discover** repositories containing target code patterns
- Results are deduplicated by repository name in post-processing

#### 1.2 Repository-Scoped Code Search

**Method**: `search_code_in_repository()`

**Purpose**: Search for code patterns within a specific repository. Currently implemented but not actively used in the main workflow.

**Request Format**:
```http
GET https://api.github.com/search/code
Authorization: token <GITHUB_TOKEN>
```

**Query Parameters**:
- `q` (string, required): Search query with qualifiers
  - Format: `{query} language:{language} repo:{owner}/{repo}`
  - Example: `call_user_func language:PHP repo:owner/repo`
  - **Note**: The `repo:` qualifier limits search to a specific repository

**Example Request**:
```python
url = "https://api.github.com/search/code"
params = {
    "q": "call_user_func language:PHP repo:owner/repo",  # Repository-scoped search
    "per_page": 100,
    "sort": "indexed",
    "order": "desc"
}
```

**Key Points**:
- **Requires `repo:` qualifier** - limits search to one repository
- Returns results from a single repository only
- Could be used for deeper analysis within specific repositories
- **Not currently used** in the primary project workflow

**Why Global Search is Used**:

The project's core goal is to **discover new PHP repositories** on GitHub that contain specific security risk patterns, not to analyze pre-known repositories. This is fundamentally a **discovery problem**, not an analysis problem.

**Key Reasons**:

1. **Unknown Repository List**: 
   - We don't have a predefined list of repositories to analyze
   - We need to search across ALL public repositories on GitHub
   - Global search allows searching millions of repositories simultaneously

2. **Pattern-Based Discovery**:
   - We're looking for repositories containing specific code patterns (e.g., `call_user_func`, `include $_GET`)
   - Global Code Search can find these patterns across all repositories
   - Repository-scoped search requires knowing the repository name first (chicken-and-egg problem)

3. **Search Flow**:
   ```
   Problem: Find PHP repos with security risks
   ↓
   Global Code Search: "call_user_func language:PHP"
   ↓
   Returns: List of files matching the pattern from various repos
   ↓
   Extract: Unique repository identifiers (owner/repo)
   ↓
   Result: We discovered new repositories to analyze
   ```

4. **Repository-Scoped Search Limitation**:
   - Format: `call_user_func language:PHP repo:owner/repo`
   - **Problem**: Requires knowing `owner/repo` beforehand
   - **Use Case**: Analyzing a specific known repository
   - **Not Suitable**: Discovering new repositories (we don't know which repos to search)

5. **Alternative Approaches Considered**:
   - **Repository Search API** (`/search/repositories`): Searches by metadata (name, description, topics), not code content
     - Can find: "PHP repositories with 'security' in description"
     - **Cannot find**: "Repositories containing `call_user_func` code"
   - **Repository-Scoped Code Search**: Requires repository name
     - Can search: Specific known repository
     - **Cannot**: Discover which repositories contain the pattern

**Conclusion**:
Global Code Search is the **only GitHub API** that can search for code patterns across all repositories without requiring repository names. It's essential for the discovery workflow, as we're searching for repositories based on code content, not repository metadata.

**Response Format**:
```json
{
  "total_count": 1234,
  "incomplete_results": false,
  "items": [
    {
      "name": "index.php",
      "path": "index.php",
      "sha": "...",
      "url": "https://api.github.com/repos/owner/repo/contents/index.php",
      "git_url": "...",
      "html_url": "https://github.com/owner/repo/blob/main/index.php",
      "repository": {
        "id": 123456,
        "name": "repo",
        "full_name": "owner/repo",
        "owner": {
          "login": "owner",
          ...
        },
        "html_url": "https://github.com/owner/repo",
        "stargazers_count": 100,
        ...
      },
      "score": 1.0
    }
  ]
}
```

**Key Response Fields Used**:
- `total_count`: Total number of matches
- `incomplete_results`: Whether results were truncated due to timeout
- `items[].repository.full_name`: Repository identifier
- `items[].path`: File path containing the match
- `items[].repository.html_url`: Repository URL

**Rate Limits**:
- **Authenticated requests**: 30 requests/minute
- **Unauthenticated requests**: 10 requests/minute

**Caching**:
- Cache duration: 1 hour (3600 seconds)
- Cache key: URL + query parameters

**Usage in Project**:
- **Primary usage**: Global search (`search_code_content()`) to discover repositories
- Returns file paths and repository information from multiple repositories
- Results are deduplicated by repository name (`full_name`)
- Each result contains a repository identifier, allowing tracking of unique repositories
- After discovery, file contents are fetched using File Content API for analysis

**Current Workflow**:
1. Use global Code Search to find repositories containing patterns
2. Extract unique repository identifiers from results
3. Fetch file contents for matched files using File Content API
4. Analyze file contents locally

**Note**: Repository-scoped search (`search_code_in_repository()`) exists in the codebase but is not used in the current workflow, as we need global discovery rather than repository-specific analysis.

---

### 2. Repository Search API

**Endpoint**: `GET /search/repositories`

**Purpose**: Search for repositories based on metadata (name, description, topics, etc.). Currently used for optimized repository discovery, though Code Search API is preferred for pattern matching.

**Method**: `search_repositories_optimized()`

**Request Format**:
```http
GET https://api.github.com/search/repositories
Authorization: token <GITHUB_TOKEN>
```

**Query Parameters**:
- `q` (string, required): Search query
  - Example: `language:PHP stars:>100`
- `per_page` (integer, optional): Results per page (max 100, default 30)
- `sort` (string, optional): Sort order (`stars`, `forks`, `updated`, etc.)
- `order` (string, optional): Sort direction (`asc`, `desc`)

**Example Request**:
```python
url = "https://api.github.com/search/repositories"
params = {
    "q": "language:PHP",
    "per_page": 100,
    "sort": "stars",
    "order": "desc"
}
```

**Response Format**:
```json
{
  "total_count": 5000,
  "incomplete_results": false,
  "items": [
    {
      "id": 123456,
      "name": "repo",
      "full_name": "owner/repo",
      "owner": {
        "login": "owner",
        ...
      },
      "html_url": "https://github.com/owner/repo",
      "description": "...",
      "stargazers_count": 100,
      "default_branch": "main",
      ...
    }
  ]
}
```

**Rate Limits**:
- **Authenticated requests**: 30 requests/minute
- **Unauthenticated requests**: 10 requests/minute

**Caching**:
- Cache duration: 2 hours (7200 seconds)
- Cache key: URL + query parameters

**Usage in Project**:
- Secondary method for repository discovery
- Provides repository metadata (stars, description, etc.)
- Less frequently used compared to Code Search API

---

### 3. Repository Contents API

**Endpoint**: `GET /repos/{owner}/{repo}/contents`

**Purpose**: Get the contents of the root directory of a repository. Used as a fallback method when Code Search API file paths are not available.

**Method**: `get_repository_contents()`

**Request Format**:
```http
GET https://api.github.com/repos/{owner}/{repo}/contents
Authorization: token <GITHUB_TOKEN>
```

**Path Parameters**:
- `owner` (string, required): Repository owner username
- `repo` (string, required): Repository name

**Query Parameters**:
- `ref` (string, optional): Branch/tag name (default: repository's default branch)

**Example Request**:
```python
url = "https://api.github.com/repos/owner/repo/contents"
# No query parameters needed for root directory
```

**Response Format**:
```json
[
  {
    "type": "file",
    "name": "index.php",
    "path": "index.php",
    "sha": "...",
    "size": 1024,
    "url": "https://api.github.com/repos/owner/repo/contents/index.php",
    "html_url": "https://github.com/owner/repo/blob/main/index.php",
    "git_url": "...",
    "download_url": "..."
  },
  {
    "type": "dir",
    "name": "src",
    "path": "src",
    ...
  }
]
```

**Key Response Fields Used**:
- `items[].type`: `"file"` or `"dir"`
- `items[].name`: File or directory name
- `items[].path`: Full path relative to repository root
- Filtered to only include files with `.php` extension

**Rate Limits**:
- **Authenticated requests**: 5000 requests/hour
- **Unauthenticated requests**: 60 requests/hour

**Caching**:
- Cache duration: 30 minutes (1800 seconds)
- Cache key: URL (no parameters)

**Usage in Project**:
- Fallback method when Code Search API doesn't provide file paths
- Used to scan repository root directory for PHP files
- Limited to first 10 PHP files found

---

### 4. File Content API

**Endpoint**: `GET /repos/{owner}/{repo}/contents/{path}`

**Purpose**: Get the full content of a specific file in a repository. Used to fetch complete PHP file contents for analysis.

**Method**: `get_file_content()`

**Request Format**:
```http
GET https://api.github.com/repos/{owner}/{repo}/contents/{path}
Authorization: token <GITHUB_TOKEN>
```

**Path Parameters**:
- `owner` (string, required): Repository owner username
- `repo` (string, required): Repository name
- `path` (string, required): File path relative to repository root

**Query Parameters**:
- `ref` (string, optional): Branch/tag name (default: repository's default branch)

**Example Request**:
```python
url = "https://api.github.com/repos/owner/repo/contents/src/index.php"
```

**Response Format**:
```json
{
  "type": "file",
  "encoding": "base64",
  "size": 1024,
  "name": "index.php",
  "path": "src/index.php",
  "content": "PD9waHAKICAgIC8vIFBocCBjb2RlIGV4YW1wbGUKICAgIC4uLgo=",
  "sha": "...",
  "url": "...",
  "html_url": "...",
  "download_url": "..."
}
```

**Key Response Fields Used**:
- `content`: Base64-encoded file content (requires decoding)
- `size`: File size in bytes
- `encoding`: Always `"base64"` for text files

**Processing**:
```python
import base64
content = base64.b64decode(file_data["content"]).decode("utf-8")
```

**Rate Limits**:
- **Authenticated requests**: 5000 requests/hour
- **Unauthenticated requests**: 60 requests/hour

**Caching**:
- Cache duration: 30 minutes (1800 seconds)
- Cache key: URL (no parameters)

**Usage in Project**:
- Primary method for fetching file contents after Code Search API identifies files
- Used to get complete PHP file content for Semgrep and regex analysis
- Limited to 10 files per repository to manage API usage

---

### 5. Repository Info API

**Endpoint**: `GET /repos/{owner}/{repo}`

**Purpose**: Get detailed information about a specific repository, including metadata, statistics, and configuration.

**Method**: `get_repository_info()`

**Request Format**:
```http
GET https://api.github.com/repos/{owner}/{repo}
Authorization: token <GITHUB_TOKEN>
```

**Path Parameters**:
- `owner` (string, required): Repository owner username
- `repo` (string, required): Repository name

**Example Request**:
```python
url = "https://api.github.com/repos/owner/repo"
```

**Response Format**:
```json
{
  "id": 123456,
  "name": "repo",
  "full_name": "owner/repo",
  "owner": {
    "login": "owner",
    ...
  },
  "html_url": "https://github.com/owner/repo",
  "description": "...",
  "stargazers_count": 100,
  "watchers_count": 50,
  "forks_count": 20,
  "default_branch": "main",
  "language": "PHP",
  "created_at": "2020-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z",
  ...
}
```

**Key Response Fields Used**:
- `full_name`: Repository identifier
- `html_url`: Repository URL
- `stargazers_count`: Number of stars
- `default_branch`: Default branch name
- `description`: Repository description

**Rate Limits**:
- **Authenticated requests**: 5000 requests/hour
- **Unauthenticated requests**: 60 requests/hour

**Caching**:
- Cache duration: 1 hour (3600 seconds)
- Cache key: URL (no parameters)

**Usage in Project**:
- Currently less frequently used
- Provides repository metadata for SearchResult objects
- Used when additional repository information is needed

---

## API Request Flow

### Primary Workflow

1. **Code Search API (Global)** (`/search/code`)
   - **Query format**: `{pattern} language:PHP` (without `repo:` qualifier)
   - **Example**: `call_user_func language:PHP`
   - **Returns**: List of files containing the pattern from various repositories
   - **Purpose**: Discover relevant repositories across all of GitHub
   - **Note**: Uses global search, not repository-scoped search

2. **Extract Repository Information**
   - From Code Search results, extract unique repository identifiers (`full_name`)
   - Collect all matched file paths for each repository
   - Deduplicate repositories to avoid analyzing the same repo multiple times

3. **File Content API** (`/repos/{owner}/{repo}/contents/{path}`)
   - Fetch complete file contents for matched files from step 1
   - Uses file paths directly from Code Search results
   - **Purpose**: Get full PHP code for analysis
   - **Limit**: Maximum 10 files per repository

4. **Analysis** (Local)
   - Use Semgrep and regex to analyze file contents
   - **Purpose**: Detect security risk patterns (SuperGlobal usage, dynamic functions, dynamic includes)

### Fallback Workflow

If Code Search API doesn't provide file paths for a repository:

1. **Repository Contents API** (`/repos/{owner}/{repo}/contents`)
   - List repository root directory contents
   - Filter for `.php` files
   - **Purpose**: Find PHP files to analyze when Code Search file paths unavailable

2. **File Content API** (as above)
   - Fetch selected PHP file contents from root directory scan
   - **Limit**: Maximum 10 files per repository

---

## Rate Limiting

### Rate Limit Headers

GitHub API returns rate limit information in response headers:

```
X-RateLimit-Limit: 5000
X-RateLimit-Remaining: 4990
X-RateLimit-Used: 10
X-RateLimit-Reset: 1609459200
```

### Rate Limit Handling

The project implements automatic rate limit handling:

1. **Pre-request Check**: Check remaining requests before each API call
2. **Wait Mechanism**: Automatically wait if approaching rate limit
3. **Update from Response**: Parse and update rate limit status after each response
4. **Exponential Backoff**: Implemented for rate limit errors

### Rate Limit Thresholds

- **Code Search API**: 
  - Remaining < 5: Wait before next request
  - Reset time < 1 hour away: Wait for reset
- **Other APIs**: 
  - Remaining < 100: Warning logged
  - Reset time < 1 hour away: Wait for reset

---

## Caching Strategy

### Cache Implementation

All API responses are cached using SQLite database to minimize API requests:

**Cache Manager** (`src/cache_manager.py`):
- Stores responses with expiration times
- Cache keys: URL + parameters (JSON serialized)
- Automatic cleanup of expired entries

### Cache Durations

| API Endpoint | Cache Duration | Reason |
|--------------|---------------|--------|
| `/search/code` | 1 hour | Code search results may change frequently |
| `/search/repositories` | 2 hours | Repository metadata changes less frequently |
| `/repos/{owner}/{repo}/contents` | 30 minutes | Directory contents may change |
| `/repos/{owner}/{repo}/contents/{path}` | 30 minutes | File contents may change |
| `/repos/{owner}/{repo}` | 1 hour | Repository info changes infrequently |

### Cache Key Generation

```python
def generate_cache_key(url: str, params: Optional[Dict] = None) -> str:
    """Generate cache key from URL and parameters"""
    key_parts = [url]
    if params:
        key_parts.append(json.dumps(params, sort_keys=True))
    return hashlib.md5("|".join(key_parts).encode()).hexdigest()
```

---

## Error Handling

### HTTP Status Codes

| Status Code | Meaning | Handling |
|-------------|---------|----------|
| 200 | Success | Process response normally |
| 401 | Unauthorized | Invalid or missing token |
| 403 | Forbidden | Rate limit exceeded or insufficient permissions |
| 404 | Not Found | File/repository doesn't exist |
| 422 | Unprocessable Entity | Invalid query format |
| 429 | Too Many Requests | Rate limit exceeded |
| 500+ | Server Error | Retry with exponential backoff |

### Error Response Format

```json
{
  "message": "API rate limit exceeded",
  "documentation_url": "https://docs.github.com/..."
}
```

### Custom Exception Classes

- `GitHubAPIError`: General GitHub API errors
  - Attributes: `status_code`, `error_text`
- `RateLimitError`: Rate limit exceeded
  - Attributes: `reset_time`, `remaining`

---

## Best Practices

### Query Optimization

1. **Use Specific Qualifiers**: 
   - Always include `language:PHP` in code searches
   - Use repository limits when possible: `repo:owner/repo`

2. **Combine Queries**: 
   - Use OR to combine related patterns: `call_user_func OR call_user_func_array language:PHP`
   - Limit query groups to 2-3 patterns to avoid query length issues

3. **Sort Strategies**:
   - Code Search: `sort=indexed` (finds recently indexed code)
   - Repository Search: `sort=stars` (finds popular repositories)

### Request Optimization

1. **Cache Everything**: All API responses are cached
2. **Batch Operations**: Group related requests when possible
3. **Limit File Fetching**: Only fetch first 10 PHP files per repository
4. **Use Code Search Results**: Directly use file paths from Code Search API instead of scanning repositories

### Authentication

- Always use personal access tokens
- Store tokens securely (config file or environment variables)
- Never commit tokens to version control

---

## API Usage Statistics

Based on the project workflow:

1. **Code Search API**: ~4-8 requests per search session (one per query group)
2. **File Content API**: ~10-100 requests per analysis (one per PHP file)
3. **Repository Contents API**: ~0-10 requests (fallback only)
4. **Repository Info API**: ~0-10 requests (less frequently used)

**Estimated API Usage per 100 Projects**:
- Code Search: 4-8 requests
- File Content: 100-1000 requests (10 files × 10-100 projects)
- Total: ~104-1018 requests (well within 5000/hour limit)

---

## Reference Links

- [GitHub REST API Documentation](https://docs.github.com/en/rest)
- [Code Search API](https://docs.github.com/en/rest/search/search#search-code)
- [Repository Search API](https://docs.github.com/en/rest/search/search#search-repositories)
- [Repository Contents API](https://docs.github.com/en/rest/repos/contents)
- [Rate Limiting](https://docs.github.com/en/rest/rate-limit)

