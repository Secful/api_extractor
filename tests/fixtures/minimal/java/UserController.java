package com.example.api.controllers;

import org.springframework.web.bind.annotation.*;
import java.util.List;

class CreateUserRequest {
    private String username;
    private String email;

    public String getUsername() { return username; }
    public void setUsername(String username) { this.username = username; }
    public String getEmail() { return email; }
    public void setEmail(String email) { this.email = email; }
}

class User {
    private Long id;
    private String username;
    private String email;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getUsername() { return username; }
    public void setUsername(String username) { this.username = username; }
    public String getEmail() { return email; }
    public void setEmail(String email) { this.email = email; }
}

@RestController
@RequestMapping("/api/users")
public class UserController {

    @GetMapping
    public List<User> getAllUsers() {
        return null;
    }

    @GetMapping("/{id}")
    public User getUser(@PathVariable Long id) {
        return null;
    }

    @PostMapping
    public User createUser(@RequestBody CreateUserRequest request) {
        return null;
    }

    @PutMapping("/{id}")
    public User updateUser(@PathVariable Long id, @RequestBody CreateUserRequest request) {
        return null;
    }

    @DeleteMapping("/{id}")
    public void deleteUser(@PathVariable Long id) {
    }

    @GetMapping("/search")
    public List<User> searchUsers(
        @RequestParam String query,
        @RequestParam(required = false) Integer limit
    ) {
        return null;
    }
}
