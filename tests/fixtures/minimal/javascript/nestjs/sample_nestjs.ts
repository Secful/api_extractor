/**
 * Sample NestJS application for testing.
 */

import { Controller, Get, Post, Put, Delete, Body, Param, Query } from '@nestjs/common';

class CreateUserDto {
  username: string;
  email: string;
}

// Simple string path
@Controller('users')
export class UserController {
  @Get()
  findAll(@Query('skip') skip?: number, @Query('limit') limit?: number) {
    return { skip, limit };
  }

  @Get(':id')
  findOne(@Param('id') id: string) {
    return { id };
  }

  @Post()
  create(@Body() createUserDto: CreateUserDto) {
    return createUserDto;
  }

  @Put(':id')
  update(@Param('id') id: string, @Body() updateUserDto: any) {
    return { id, ...updateUserDto };
  }

  @Delete(':id')
  remove(@Param('id') id: string) {
    return { deleted: id };
  }
}

// Object syntax with versioning
@Controller({ path: 'products', version: '1' })
export class ProductController {
  @Get()
  list() {
    return [];
  }

  @Get(':productId')
  getProduct(@Param('productId') productId: string) {
    return { id: productId };
  }

  @Post()
  createProduct(@Body() product: any) {
    return product;
  }
}

// Empty @Get() should create root route
@Controller('health')
export class HealthController {
  @Get()
  check() {
    return { status: 'ok' };
  }
}

// Nested paths
@Controller('api/orders')
export class OrderController {
  @Get()
  findAll() {
    return [];
  }

  @Get(':orderId/items')
  getOrderItems(@Param('orderId') orderId: string) {
    return [];
  }
}
