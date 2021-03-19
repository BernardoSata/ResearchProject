// SPDX-License-Identifier: MIT
pragma solidity >=0.4.22 <0.9.0;

library Planning {

    struct Position {
        int x;
        int y;
    }

    struct Volume {
        uint len;
        uint height;
        uint depth;
    }

    struct Vehicle {
        Position position;
        uint max_payload;
        Volume max_volume;
        uint distance_left;
        //Avaraged values
        uint speed;
        uint set_up_time;
        uint drop_off_time;
        uint time_for_task;
    }

    struct Request {
        Position source;
        Position destination;
        uint weight;
        Volume volume;
    }
}