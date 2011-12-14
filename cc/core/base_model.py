# Case Conductor is a Test Case Management system.
# Copyright (C) 2011 uTest Inc.
#
# This file is part of Case Conductor.
#
# Case Conductor is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Case Conductor is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Case Conductor.  If not, see <http://www.gnu.org/licenses/>.
"""
Common model behavior for all Case Conductor models.

Soft-deletion (including cascade) and tracking of user and timestamp for model
creation, modification, and soft-deletion.

@@@ implement cascade of soft-delete

"""
import datetime

from django.db import models
from django.db.models.query import QuerySet

from django.contrib.auth.models import User



def utcnow():
    return datetime.datetime.utcnow()



class BaseQuerySet(QuerySet):
    """
    Implements modification tracking and soft deletes on bulk update/delete.

    """
    def create(self, *args, **kwargs):
        """
        Creates, saves, and returns a new object with the given kwargs.
        """
        user = kwargs.pop("user", None)
        kwargs["created_by"] = user
        kwargs["modified_by"] = user
        return super(BaseQuerySet, self).create(*args, **kwargs)


    def update(self, *args, **kwargs):
        """
        Update all objects in this queryset with modifications in ``kwargs``.

        """
        kwargs["modified_by"] = kwargs.pop("user", None)
        kwargs["modified_on"] = utcnow()
        return super(BaseQuerySet, self).update(*args, **kwargs)


    def delete(self, user=None):
        """
        Soft-delete all objects in this queryset.

        """
        # super update, not our update, because we don't want to track
        # soft-deletion as a modification; that would be a waste of modified-by
        # and modified-on, since they would just duplicate deleted-by and
        # deleted-on.
        super(BaseQuerySet, self).update(
            deleted_by=user, deleted_on=utcnow())



class BaseManager(models.Manager):
    """Pass-through manager to ensure ``BaseQuerySet`` is always used."""
    def get_query_set(self):
        """Return a ``BaseQuerySet`` for all queries."""
        return BaseQuerySet(self.model, using=self._db)



class NotDeletedManager(BaseManager):
    """Manager that returns only not-deleted objects."""
    def get_query_set(self):
        return super(NotDeletedManager, self).get_query_set().filter(
            deleted_on__isnull=True)



class BaseModel(models.Model):
    """
    Common base abstract model for all Case Conductor models.

    Tracks user and timestamp for creation, modification, and (soft) deletion.

    """
    created_by = models.ForeignKey(User, null=True, related_name="+")
    modified_by = models.ForeignKey(User, null=True, related_name="+")
    deleted_by = models.ForeignKey(User, null=True, related_name="+")

    created_on = models.DateTimeField(default=utcnow)
    modified_on = models.DateTimeField(default=utcnow)
    deleted_on = models.DateTimeField(db_index=True, null=True)


    # default manager returns all objects, so admin can see all
    everything = BaseManager()
    # ...but "objects", for use in most code, returns only not-deleted
    objects = NotDeletedManager()


    def save(self, *args, **kwargs):
        """
        Save this instance, recording modified timestamp and user.

        """
        user = kwargs.pop("user", None)
        now = utcnow()
        if self.pk is None and user is not None:
            self.created_by = user
        if self.pk or user is not None:
            self.modified_by = user
        self.modified_on = now
        return super(BaseModel, self).save(*args, **kwargs)


    def delete(self, user=None):
        """
        (Soft) delete this instance.

        """
        self.deleted_by = user
        self.deleted_on = utcnow()
        # super save, not ours; don't want to track deletion as modification
        super(BaseModel, self).save()


    class Meta:
        abstract = True