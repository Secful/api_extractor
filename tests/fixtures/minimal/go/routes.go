package main

import "github.com/gin-gonic/gin"

func ProductsRegister(router *gin.RouterGroup) {
	router.GET("", GetProducts)
	router.GET("/:id", GetProduct)
	router.POST("", CreateProduct)
	router.PUT("/:id", UpdateProduct)
	router.DELETE("/:id", DeleteProduct)
	router.GET("/search", SearchProducts)
}

func GetProducts(c *gin.Context) {}
func GetProduct(c *gin.Context) {}
func CreateProduct(c *gin.Context) {}
func UpdateProduct(c *gin.Context) {}
func DeleteProduct(c *gin.Context) {}
func SearchProducts(c *gin.Context) {}
