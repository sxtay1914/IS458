package com.fashionstore.catalog;

import com.fashionstore.common.ApiException;
import java.util.List;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/products")
public class CatalogController {

    private final CatalogRepository repo;

    public CatalogController(CatalogRepository repo) {
        this.repo = repo;
    }

    @GetMapping
    List<Product> list(@RequestParam(required = false) String category,
                       @RequestParam(name = "in_stock", required = false) Boolean inStock) {
        return repo.list(category, inStock);
    }

    @GetMapping("/{sku}")
    Product get(@PathVariable String sku) {
        return repo.find(sku).orElseThrow(() -> ApiException.notFound("Product"));
    }
}
