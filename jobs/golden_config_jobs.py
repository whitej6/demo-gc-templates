from nautobot_golden_config.jobs import commit_check, FormEntry
from nautobot_golden_config.utilities.git import GitRepo
from nautobot_golden_config.utilities.helper import get_job_filter
from nautobot_golden_config.nornir_plays.config_intended import config_intended
from nautobot_golden_config.nornir_plays.config_compliance import config_compliance

from nautobot.extras.datasources.git import ensure_git_repository
from nautobot.extras.jobs import BooleanVar, Job

name = "Patched Golden Config Jobs"


def get_refreshed_repos(job, repo_type, data=None):
    site_slugs = get_job_filter(data).values_list("site__slug").distinct()
    repos = []
    for site in site_slugs:
        LOGGER.debug(f"Pull Repo for site {site}.")
        repo = GitRepository.objects.get(slug=f"{repo_type}-{site}")
        ensure_git_repository(repo, job_obj.job_result)
        repos.append(repo)
    return repos

class RefreshRepos(Job, FormEntry):
    """Job to to run the compliance engine."""

    tenant_group = FormEntry.tenant_group
    tenant = FormEntry.tenant
    region = FormEntry.region
    site = FormEntry.site
    rack_group = FormEntry.rack_group
    rack = FormEntry.rack
    role = FormEntry.role
    manufacturer = FormEntry.manufacturer
    platform = FormEntry.platform
    device_type = FormEntry.device_type
    device = FormEntry.device
    tag = FormEntry.tag
    debug = FormEntry.debug
    class Meta:
        name = "Only Refreshed Repos for Golden Config."

    @commit_check
    def run(self, data, commit):  # pylint: disable=too-many-branches
        LOGGER.debug("Pull Intended config repos.")
        get_refreshed_repos(job_obj=self, repo_type="intended", data=data)
        LOGGER.debug("Pull Backup config repos.")
        get_refreshed_repos(job_obj=self, repo_type="backup", data=data)


class ComplianceJob(Job, FormEntry):
    """Job to to run the compliance engine."""

    tenant_group = FormEntry.tenant_group
    tenant = FormEntry.tenant
    region = FormEntry.region
    site = FormEntry.site
    rack_group = FormEntry.rack_group
    rack = FormEntry.rack
    role = FormEntry.role
    manufacturer = FormEntry.manufacturer
    platform = FormEntry.platform
    device_type = FormEntry.device_type
    device = FormEntry.device
    tag = FormEntry.tag
    debug = FormEntry.debug
    refresh_repos = BooleanVar("Checked will refresh repos")
    class Meta:
        name = "Patched Compliance Job."

    @commit_check
    def run(self, data, commit):  # pylint: disable=too-many-branches
        if data.get("refresh_repos"):
            LOGGER.debug("Pull Intended config repos.")
            get_refreshed_repos(job_obj=self, repo_type="intended", data=data)
            LOGGER.debug("Pull Backup config repos.")
            get_refreshed_repos(job_obj=self, repo_type="backup", data=data)
        self.data = data

    def post_run(self):
        LOGGER.debug("Starting Compliance.")
        config_compliance(self, self.data)


class PatchedIntendedJob(Job, FormEntry):
    """Job to to run generation of intended configurations."""

    tenant_group = FormEntry.tenant_group
    tenant = FormEntry.tenant
    region = FormEntry.region
    site = FormEntry.site
    rack_group = FormEntry.rack_group
    rack = FormEntry.rack
    role = FormEntry.role
    manufacturer = FormEntry.manufacturer
    platform = FormEntry.platform
    device_type = FormEntry.device_type
    device = FormEntry.device
    tag = FormEntry.tag
    debug = FormEntry.debug
    class Meta:
        name = "Patched Intended Job."

    @commit_check
    def run(self, data, commit):  # pylint: disable=too-many-branches
        LOGGER.debug("Pull Intended config repos.")
        self.repos = get_refreshed_repos(job_obj=self, repo_type="intended", data=data)
        LOGGER.debug("Pull Jinja template repos.")
        _get_refreshed_repos(job_obj=self, repo_type="jinja_repository", data=data)
        self.data = data

    def post_run(self):
        LOGGER.debug("Run config intended nornir play.")
        config_intended(self, self.data)
        for intended_repo in self.repos:
            LOGGER.debug("Push new intended configs to repo %s.", intended_repo.url)
            intended_repo.commit_with_added(f"INTENDED CONFIG CREATION JOB - {now}")
            intended_repo.push()

# jobs = [PatchedComplianceJob, PatchedIntendedJob, RefreshRepos]
