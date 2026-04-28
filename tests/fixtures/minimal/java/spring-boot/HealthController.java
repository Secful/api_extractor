package com.example.api.controllers;

import org.springframework.web.bind.annotation.*;

@RestController
public class HealthController {

    @GetMapping("/health")
    public String health() {
        return "OK";
    }
}
