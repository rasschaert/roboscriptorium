#!/usr/bin/env zsh
# Stops every robo-* run while the battery is under 30% and continues them at 50%
# (ROBO_BATTERY_FLOOR, ROBO_BATTERY_RESUME), and while the disk has under 5 GB free until
# 15 GB, checking each minute; prints each change and every 5% (priority.guard). Runs in its own screen, robo-battery-guard, which it leaves
# running: experiments/detached.sh battery-guard experiments/battery_guard.sh
# resumes: holds no state; a stop leaves stopped runs stopped (continue them with kill -CONT)
# models: none
cd /Users/kenny.rasschaert/code/roboscriptorium
exec uv run python -m roboscriptorium.priority
