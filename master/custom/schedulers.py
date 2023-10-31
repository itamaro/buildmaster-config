import re
from buildbot.schedulers.basic import AnyBranchScheduler
from twisted.internet import defer
from twisted.python import log


class GitHubPrScheduler(AnyBranchScheduler):
    def __init__(self, *args, stable_builder_names, **kwargs):
        super().__init__(*args, **kwargs)
        self.stable_builder_names = stable_builder_names
        log.msg(f"GitHubPrScheduler init, stable builder names: {self.stable_builder_names}")

    @defer.inlineCallbacks
    def addBuildsetForChanges(self, **kwargs):
        log.msg("Preapring buildset for PR changes")
        changeids = kwargs.get("changeids")
        if changeids is None or len(changeids) != 1:
            log.msg("No changeids or more than one changeid found")
            yield super().addBuildsetForChanges(**kwargs)
            return

        changeid = changeids[0]
        chdict = yield self.master.db.changes.getChange(changeid)

        builder_filter = chdict["properties"].get("builderfilter", None)
        event = chdict["properties"].get("event", None)
        if event:
            event, _ = event
        builder_names = kwargs.get("builderNames", self.builderNames)
        log.msg(f"Builder filter: {builder_filter}, event: {event}, builder names: {builder_names}")
        if builder_filter and builder_names:
            # allow unstable builders only for comment-based trigger
            if event != "issue_comment":
                builder_names = [
                    builder_name
                    for builder_name in builder_names
                    if builder_name in self.stable_builder_names
                ]
                log.msg(f"Filtered builder names: {builder_names}")
            log.msg("Found builder filter: {}".format(builder_filter))
            builder_filter, _ = builder_filter
            matcher = re.compile(builder_filter, re.IGNORECASE)
            log.msg(f"Builder names pre-matcher: {builder_names}")
            builder_names = [
                builder_name
                for builder_name in builder_names
                if matcher.search(builder_name)
            ]
            log.msg(f"Builder names filtered: {builder_names}")
            kwargs.update(builderNames=builder_names)
            yield super().addBuildsetForChanges(**kwargs)
            return

        log.msg("Scheduling regular non-filtered buildset")
        yield super().addBuildsetForChanges(**kwargs)
        return
