#!/usr/bin/env bats

@test "stunnel is installed and is in the PATH" {
  command -v stunnel
}

@test "should have stunnel running" {
  [ "$(ps aux | grep stunnel | grep -v grep)" ]
}
