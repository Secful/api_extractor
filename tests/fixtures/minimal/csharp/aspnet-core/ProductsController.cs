using Microsoft.AspNetCore.Mvc;
using System.Collections.Generic;

namespace ApiExtractorTest.Controllers
{
    public class Product
    {
        public int Id { get; set; }
        public string Name { get; set; }
        public decimal Price { get; set; }
    }

    [ApiController]
    [Route("api/[controller]")]
    public class ProductsController : ControllerBase
    {
        [HttpGet]
        public IEnumerable<Product> GetAll()
        {
            return new List<Product>();
        }

        [HttpGet("{id}")]
        public Product GetById([FromRoute] int id)
        {
            return null;
        }

        [HttpPost]
        public Product Create([FromBody] Product product)
        {
            return null;
        }

        [HttpPut("{id}")]
        public Product Update([FromRoute] int id, [FromBody] Product product)
        {
            return null;
        }

        [HttpDelete("{id}")]
        public void Delete([FromRoute] int id)
        {
        }

        [HttpGet("search")]
        public IEnumerable<Product> Search([FromQuery] string query, [FromQuery] int? limit)
        {
            return new List<Product>();
        }
    }
}
