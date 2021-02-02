batch
===

This role provides basic infrastructure to run sharded ephemeral batch
jobs on a *float* cluster. The idea is to use Ansible to distribute
the input to the various hosts, according to their *shard_id*, and
then use GNU parallel as the local job runner on the hosts.

The idea is to use Ansible to start the batch processing job.  It
should eventually be possible to use Ansible again to check for its
completion, but this isn't possible yet.

## Input data

The input data consists of a file containing a series of commands, one
per line, prefixed by the *shard_id* identifying the host that the
command should be run on. Think of it like a partitioned *xargs*
invocation.

Simple operations can be mapped pretty easily to this model: for
instance, suppose we have a map of our partitioned user accounts such
as the following (user -> shard_id):

```
{
  "user1": "host1",
  "user2": "host2",
  ...
}
```

and we want to invoke the *fix-user* command on each account, the
input data will look like

```
host1 fix-user user1
host2 fix-user user2
...
```

it's pretty straightforward to see how this can be generated from the
usermap.

## Usage

The role is meant to be used from a custom playbook, using the
*input_file* variable to point at the input data:

```yaml
---

- hosts: backend
  roles: batch
  vars:
    job_name: test-batch-job
    input_file: input.dat
```

(there's probably a way to make this an ansible one-liner).

The *job_name* variable must be defined: it will be used to generate a
unique identifier for the batch job by combining it with a MD5 of the
input data file.
